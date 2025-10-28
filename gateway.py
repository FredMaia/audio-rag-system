from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WHISPER_SERVICE_URL = os.getenv("WHISPER_SERVICE_URL", "http://localhost:8001")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8002")

@app.get("/")
async def root():
    return {"message": "API Gateway Online"}

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    """
    Recebe um arquivo de áudio, transcreve via Whisper e processa via RAG
    """
    try:
        # 1. Enviar áudio para o serviço Whisper
        audio_content = await file.read()
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Transcrição
            files = {"file": (file.filename, audio_content, file.content_type)}
            whisper_response = await client.post(
                f"{WHISPER_SERVICE_URL}/transcribe",
                files=files
            )
            logging.info(f"Whisper responded {whisper_response.status_code}: {whisper_response.text[:200]}")
            
            if whisper_response.status_code != 200:
                logging.error(f"Erro na transcrição: {whisper_response.status_code} - {whisper_response.text}")
                raise HTTPException(
                    status_code=whisper_response.status_code,
                    detail=f"Erro na transcrição: {whisper_response.text}"
                )
            
            transcription_data = whisper_response.json()
            transcribed_text = transcription_data.get("text", "")
            
            # 2. Enviar texto transcrito para o serviço RAG
            rag_response = await client.post(
                f"{RAG_SERVICE_URL}/query",
                json={"question": transcribed_text}
            )
            logging.info(f"RAG responded {rag_response.status_code}: {rag_response.text[:200]}")
            
            if rag_response.status_code != 200:
                logging.error(f"Erro no RAG: {rag_response.status_code} - {rag_response.text}")
                raise HTTPException(
                    status_code=rag_response.status_code,
                    detail=f"Erro no RAG: {rag_response.text}"
                )
            
            rag_data = rag_response.json()
            
            return {
                "transcription": transcribed_text,
                "answer": rag_data.get("answer", ""),
                "model": rag_data.get("model", "")
            }
            
    except httpx.RequestError as e:
        logging.exception("Erro de rede ao chamar serviços externos")
        raise HTTPException(status_code=503, detail=f"Erro ao conectar aos serviços: {str(e)}")
    except HTTPException:
        # repropaga já formatado
        raise
    except Exception as e:
        logging.exception("Erro interno no gateway")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)