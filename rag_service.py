from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Optional
import os
from dotenv import load_dotenv
import PyPDF2
import io
import re
import uuid

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Audio rag system")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

if not GROQ_API_KEY:
    logging.error("GROQ_API_KEY não configurada")
    raise ValueError("GROQ_API_KEY não configurada")

client = Groq(api_key=GROQ_API_KEY)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Usa PersistentClient para garantir que os dados sejam salvos no disco
chroma_client = chromadb.PersistentClient(path="./chroma_db")

try:
    collection = chroma_client.get_collection("knowledge_base")
    logging.info(f"Coleção existente carregada com {collection.count()} documentos")
except:
    collection = chroma_client.create_collection(
        name="knowledge_base",
        metadata={"description": "Base de conhecimento RAG"}
    )
    logging.info("Nova coleção criada")


class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5
    similarity_threshold: Optional[float] = 0.1

class DocumentRequest(BaseModel):
    text: str
    metadata: Optional[dict] = {}

def clean_text(text: str) -> str:
    """Limpa e normaliza texto extraído de PDF - versão mais permissiva"""
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()

def chunk_text_with_overlap(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Divide texto em chunks menores e mais focados"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end < len(text):
            last_period = text[start:end].rfind('.')
            if last_period > chunk_size * 0.5:  
                end = start + last_period + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap if end < len(text) else end
    
    return chunks

@app.get("/")
async def root():
    doc_count = collection.count()
    return {
        "message": "RAG Service with Embeddings Online",
        "provider": "Groq",
        "vector_db": "ChromaDB",
        "embedding_model": "all-MiniLM-L6-v2",
        "documents_count": doc_count
    }

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Extrai texto de um PDF e adiciona à base de conhecimento"""
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")
        
        contents = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
        total_pages = len(pdf_reader.pages)
        
        extracted_text = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text.strip():
                cleaned = clean_text(text)
                if cleaned:
                    extracted_text.append(cleaned)
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="Não foi possível extrair texto do PDF")
        
        full_text = "\n\n".join(extracted_text)
        
        # Chunks menores para melhor precisão
        chunks = chunk_text_with_overlap(full_text, chunk_size=800, overlap=150)
        
        added_chunks = []
        for idx, chunk in enumerate(chunks):
            embedding = embedding_model.encode(chunk).tolist()
            doc_id = str(uuid.uuid4())
            
            metadata = {
                "source": file.filename,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "total_pages": total_pages,
                "chunk_length": len(chunk)
            }
            
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[metadata],
                ids=[doc_id]
            )
            added_chunks.append(doc_id)
        
        logging.info(f"PDF processado: {file.filename} - {len(chunks)} chunks adicionados")
        
        return {
            "status": "success",
            "filename": file.filename,
            "total_pages": total_pages,
            "chunks_added": len(chunks),
            "document_ids": added_chunks,
            "message": f"PDF processado com sucesso! {len(chunks)} fragmentos adicionados."
        }
        
    except PyPDF2.errors.PdfReadError:
        logging.exception("Erro ao ler PDF")
        raise HTTPException(status_code=400, detail="Arquivo PDF corrompido ou inválido")
    except Exception as e:
        logging.exception("Erro ao processar PDF")
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")

@app.post("/add-document")
async def add_document(doc: DocumentRequest):
    """Adiciona um documento à base de conhecimento"""
    try:
        cleaned_text = clean_text(doc.text)
        embedding = embedding_model.encode(cleaned_text).tolist()
        doc_id = str(uuid.uuid4())
        
        collection.add(
            embeddings=[embedding],
            documents=[cleaned_text],
            metadatas=[doc.metadata],
            ids=[doc_id]
        )
        
        logging.info(f"Documento adicionado: {doc_id}")
        return {
            "status": "success",
            "document_id": doc_id,
            "message": "Documento adicionado à base de conhecimento"
        }
        
    except Exception as e:
        logging.exception("Erro ao adicionar documento")
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar documento: {str(e)}")

@app.post("/query")
async def query_rag(request: QueryRequest):
    """Processa uma pergunta usando RAG com busca vetorial"""
    try:
        if collection.count() == 0:
            return {
                "question": request.question,
                "answer": "A base de conhecimento está vazia. Por favor, adicione documentos antes de fazer perguntas.",
                "sources": [],
                "model": "N/A"
            }
        
        question_embedding = embedding_model.encode(request.question).tolist()
        
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=min(request.top_k * 3, 15)  # Busca até 15 resultados
        )
        
        relevant_docs = results['documents'][0] if results['documents'] else []
        distances = results['distances'][0] if results['distances'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        
        if not metadatas:
            metadatas = [{}] * len(relevant_docs)
        
        filtered_docs = []
        filtered_distances = []
        filtered_metadata = []
        
        for doc, dist, meta in zip(relevant_docs, distances, metadatas):
            if meta is None:
                meta = {}
            
            similarity = 1 - dist
            logging.info(f"Similaridade: {similarity:.3f} (threshold: {request.similarity_threshold})")
            
            if similarity >= request.similarity_threshold:
                filtered_docs.append(doc)
                filtered_distances.append(dist)
                filtered_metadata.append(meta)
        
        filtered_docs = filtered_docs[:request.top_k]
        filtered_distances = filtered_distances[:request.top_k]
        filtered_metadata = filtered_metadata[:request.top_k]
        
        logging.info(f"Documentos após filtro: {len(filtered_docs)}")
        
        if not filtered_docs:
            if relevant_docs:
                best_similarity = 1 - distances[0]
                return {
                    "question": request.question,
                    "answer": f"Não encontrei informações com alta confiança para responder sua pergunta. O documento mais próximo tem similaridade de {best_similarity:.2%}. Tente reformular a pergunta ou adicionar mais documentos à base de conhecimento.",
                    "sources": [],
                    "model": "N/A",
                    "debug": {
                        "best_similarity": round(best_similarity, 3),
                        "threshold": request.similarity_threshold
                    }
                }
            
            return {
                "question": request.question,
                "answer": "Desculpe, não encontrei informações relevantes na base de conhecimento para responder sua pergunta.",
                "sources": [],
                "model": "N/A"
            }
        
        context_parts = []
        for i, (doc, meta) in enumerate(zip(filtered_docs, filtered_metadata)):
            if not isinstance(meta, dict):
                meta = {}
            
            source = meta.get('source', 'Documento')
            chunk_idx = meta.get('chunk_index', i)
            context_parts.append(f"[Fonte: {source} - Trecho {chunk_idx + 1}]\n{doc}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        messages = [
            {
                "role": "system",
                "content": f"""Você é um assistente especializado que responde perguntas com base em documentos fornecidos.

CONTEXTO DOS DOCUMENTOS:
{context}

INSTRUÇÕES IMPORTANTES:
- Responda SEMPRE com base nas informações do contexto acima
- Se o contexto contém a resposta (mesmo que parcialmente), apresente-a de forma clara
- Cite os artigos, seções ou fontes específicas mencionadas no contexto
- Seja direto e objetivo: evite frases como "o documento não menciona" se houver informação útil
- Use linguagem natural e clara
- Se a informação for incompleta, responda com o que está disponível e indique o que falta
- IMPORTANTE: Considere sinônimos e termos relacionados ao interpretar a pergunta"""
            },
            {
                "role": "user",
                "content": request.question
            }
        ]
        
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.6,  # Aumentado de 0.4 para 0.6 - mais flexível
            max_tokens=1024,
            top_p=0.9
        )
        answer = chat_completion.choices[0].message.content
        
        return {
            "question": request.question,
            "answer": answer,
            "sources": [
                {
                    "content": doc[:200] + "..." if len(doc) > 200 else doc,
                    "similarity": round(1 - dist, 3),
                    "metadata": meta if isinstance(meta, dict) else {}
                } 
                for doc, dist, meta in zip(filtered_docs, filtered_distances, filtered_metadata)
            ],
            "model": chat_completion.model,
            "usage": {
                "prompt_tokens": chat_completion.usage.prompt_tokens,
                "completion_tokens": chat_completion.usage.completion_tokens,
                "total_tokens": chat_completion.usage.total_tokens
            }
        }
        
    except Exception as e:
        logging.exception("Erro no RAG service")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.delete("/clear-database")
async def clear_database():
    try:
        global collection
        chroma_client.delete_collection("knowledge_base")
        collection = chroma_client.create_collection(
            name="knowledge_base",
            metadata={"description": "Base de conhecimento RAG"}
        )
        return {"status": "success", "message": "Base de conhecimento limpa"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Retorna estatísticas da base de conhecimento"""
    return {
        "total_documents": collection.count(),
        "embedding_dimension": 384,
        "model": "all-MiniLM-L6-v2"
    }

if __name__ == "__main__":
    import uvicorn
    
    logging.info(f"Base inicializada com {collection.count()} documentos")
    uvicorn.run(app, host="0.0.0.0", port=8002)