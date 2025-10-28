from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
import os
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RAG Service")

# Inicializa o cliente Groq
GROQ_API_KEY = ""
if not GROQ_API_KEY:
    logging.error("GROQ_API_KEY não configurada. Defina a variável de ambiente GROQ_API_KEY com sua chave.")
    raise ValueError("GROQ_API_KEY não configurada. Defina a variável de ambiente GROQ_API_KEY.")

client = Groq(api_key=GROQ_API_KEY)

class QueryRequest(BaseModel):
    question: str

# Contexto base para o RAG (pode ser expandido com vetorização)
KNOWLEDGE_BASE = """
Você é um assistente inteligente que responde perguntas de forma clara e objetiva.
Utilize seu conhecimento para fornecer respostas precisas e úteis.
O café da bola verde possui aroma doce.
"""

@app.get("/")
async def root():
    return {"message": "RAG Service Online", "provider": "Groq"}

@app.post("/query")
async def query_rag(request: QueryRequest):
    """
    Processa uma pergunta usando RAG com a API da Groq
    """
    try:
        # Monta o prompt com contexto
        messages = [
            {
                "role": "system",
                "content": KNOWLEDGE_BASE
            },
            {
                "role": "user",
                "content": request.question
            }
        ]
        
        # Chama a API da Groq
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",  # Modelo rápido e eficiente
                temperature=0.7,
                max_tokens=1024
            )
            answer = chat_completion.choices[0].message.content
        except Exception as e:
            logging.exception("Erro ao chamar Groq API")
            raise HTTPException(status_code=502, detail=f"Erro na API Groq: {str(e)}")
        
        return {
            "question": request.question,
            "answer": answer,
            "model": chat_completion.model,
            "usage": {
                "prompt_tokens": chat_completion.usage.prompt_tokens,
                "completion_tokens": chat_completion.usage.completion_tokens,
                "total_tokens": chat_completion.usage.total_tokens
            }
        }
        
    except HTTPException:
        # repropaga HTTPException para o FastAPI
        raise
    except Exception as e:
        logging.exception("Erro inesperado no RAG service")
        raise HTTPException(status_code=500, detail=f"Erro ao processar pergunta: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)