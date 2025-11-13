@echo off
REM --- Inicia os serviços Python ---
start cmd /k "python gateway.py"
start cmd /k "python rag_service.py"

REM --- Constrói e inicia o container do Whisper ---
docker start whisper-service

echo Todos os serviços foram iniciados!
pause