FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema necessárias para o ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements-whisper.txt .
RUN pip install --no-cache-dir -r requirements-whisper.txt

# Copia o código do serviço
COPY whisper_service.py .

# Expõe a porta
EXPOSE 8001

# Comando para iniciar o serviço
CMD ["uvicorn", "whisper_service:app", "--host", "0.0.0.0", "--port", "8001"]