docker build -f Dockerfile.whisper -t whisper-service:latest .
docker run -d --name whisper-service -p 8001:8001 --restart unless-stopped -v whisper-models:/root/.cache/whisper whisper-service:latest
pause