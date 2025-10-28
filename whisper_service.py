import warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import whisper
import tempfile
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Whisper Transcription Service",
    description="API para transcrição de áudio usando OpenAI Whisper",
    version="1.0.0"
)

# Extensões de áudio suportadas
SUPPORTED_FORMATS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm', '.mp4'}

# Carrega o modelo Whisper na inicialização
try:
    model = whisper.load_model("base")
    logger.info("Modelo Whisper carregado com sucesso: base")
except Exception as e:
    logger.exception("Falha crítica ao carregar o modelo Whisper")
    raise

@app.get("/")
async def root():
    return {
        "service": "Whisper Transcription API",
        "status": "online",
        "model": "base",
        "supported_formats": list(SUPPORTED_FORMATS)
    }

@app.get("/health")
async def health_check():
    """Endpoint para verificação de saúde do serviço"""
    return {"status": "healthy", "model_loaded": model is not None}

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcreve um arquivo de áudio usando Whisper
    
    Args:
        file: Arquivo de áudio (mp3, wav, m4a, ogg, flac, webm, mp4)
    
    Returns:
        JSON com texto transcrito, idioma e número de segmentos
    """
    tmp_file_path = None
    
    try:
        # Valida a extensão do arquivo
        suffix = os.path.splitext(file.filename)[1].lower()
        if suffix and suffix not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Formato não suportado. Use um dos seguintes: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        if not suffix:
            suffix = ".wav"  # fallback
        
        # Salva o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        logger.info(f"Arquivo recebido: {file.filename} ({len(content)} bytes)")
        
        # Transcreve o áudio
        result = model.transcribe(tmp_file_path, language="pt")
        
        logger.info(f"Transcrição concluída: {len(result['text'])} caracteres")
        
        return {
            "success": True,
            "text": result["text"],
            "language": result.get("language", "pt"),
            "segments": len(result.get("segments", [])),
            "filename": file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro ao transcrever {file.filename if file else 'arquivo'}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro na transcrição: {str(e)}"
        )
    finally:
        # Garante a limpeza do arquivo temporário
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
                logger.debug(f"Arquivo temporário removido: {tmp_file_path}")
            except Exception as e:
                logger.warning(f"Falha ao remover arquivo temporário {tmp_file_path}: {e}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler global para exceções não tratadas"""
    logger.exception("Erro não tratado")
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "Erro interno do servidor"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )