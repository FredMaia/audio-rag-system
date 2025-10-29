# 🎓 Projeto de Integração RAG + Whisper

## 🧠 Arquitetura Distribuída para Transcrição e Resposta Inteligente

### 📘 Visão Geral
Este projeto foi desenvolvido como parte das atividades acadêmicas do curso de **Ciência da Computação** na **Universidade Federal de Lavras (UFLA)**.  
Seu objetivo é integrar **modelos de transcrição de áudio (Whisper)** e **geração de respostas inteligentes (RAG com Groq API)** por meio de uma **arquitetura distribuída baseada em microsserviços**.

A solução permite o envio de um áudio, sua transcrição automática e o processamento semântico do texto resultante, retornando uma resposta inteligente ao usuário.

---

## 👥 Integrantes
- **Rafael Rezende**  
- **Frederico Maia**  
- **Mateus Mendes**  

---

## ⚙️ Arquitetura do Sistema

O sistema é composto por três microsserviços principais, orquestrados via **Docker Compose**:

```
+-----------------+       +------------------+       +----------------------+
|                 |       |                  |       |                      |
|  API Gateway    +------>+ Whisper Service  +------>+   RAG Service (Groq) |
|  (FastAPI)      |       |  (Transcrição)   |       |  (Geração de Resposta)|
|                 |       |                  |       |                      |
+-----------------+       +------------------+       +----------------------+
         |                                                         
         +--> Retorna Transcrição + Resposta Final
```

---

## 🔹 Descrição dos Componentes

### **1. Whisper Service (`whisper_service.py`)**
- Responsável pela **transcrição automática de áudios** utilizando o modelo **OpenAI Whisper (base)**.  
- Suporta múltiplos formatos: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.webm`, `.mp4`.  
- Implementado com **FastAPI** e **Uvicorn**.  
- Containerizado e exposto na **porta 8001**.

---

### **2. RAG Service (`rag_service.py`)**
- Executa a **geração de respostas contextuais** utilizando o modelo **LLaMA-3.3-70B (Groq API)**.  
- Recebe a transcrição e processa com um **contexto base embutido**.  
- Implementado com **FastAPI** e **Groq SDK**.  
- Exposto na **porta 8002**.

---

### **3. Gateway (`gateway.py`)**
- Ponto central de comunicação do sistema.  
- Responsável por:  
  1. Receber o áudio do usuário.  
  2. Encaminhar para o Whisper Service → obter transcrição.  
  3. Enviar transcrição ao RAG Service → obter resposta.  
  4. Retornar ambos ao cliente.  
- Exposto na **porta 8000**.

---

## 🧱 Estrutura do Projeto

```
📂 projeto-rag-whisper/
├── 📄 Dockerfile
├── 📄 docker-compose.yml
├── 📄 gateway.py
├── 📄 whisper_service.py
├── 📄 rag_service.py
├── 📄 requirements-gateway.txt
├── 📄 requirements-whisper.txt
├── 📄 requirements-rag.txt
└── 📁 docs/
    └── 📄 README.md (este documento)
```

---

## 🐳 Execução com Docker

### 🔧 Pré-requisitos
- **Docker** e **Docker Compose** instalados.  
- Chave de API válida da **Groq**, configurada como variável de ambiente:

```bash
export GROQ_API_KEY="sua_chave_aqui"
```

### ▶️ Passos para Execução

```bash
# Clone o repositório
git clone https://github.com/FredMaia/audio-rag-system.git
cd projeto-rag-whisper

# Inicie os serviços
docker-compose up --build
```

### 🌐 Endpoints Disponíveis
- **Gateway:** http://localhost:8000  
- **Whisper Service:** http://localhost:8001  
- **RAG Service:** http://localhost:8002  

---

## 🧩 Fluxo de Operação

1. O usuário envia um arquivo de áudio (`.mp3`, `.wav`, etc.) para o endpoint `/process-audio` do **Gateway**.  
2. O **Gateway** encaminha o áudio ao **Whisper Service** para transcrição.  
3. O texto transcrito é enviado ao **RAG Service**, que gera uma resposta contextual utilizando a **Groq API**.  
4. O **Gateway** retorna o resultado final:

```json
{
  "transcription": "texto reconhecido",
  "answer": "resposta gerada",
  "model": "llama-3.3-70b-versatile"
}
```

---

## 🧠 Tecnologias Utilizadas

| Tecnologia | Função Principal |
|-------------|------------------|
| **Python 3.10** | Linguagem base |
| **FastAPI** | Framework web dos serviços |
| **OpenAI Whisper** | Transcrição de áudio |
| **Groq API (LLaMA 3.3)** | Geração de respostas |
| **Uvicorn** | Servidor ASGI |
| **Docker Compose** | Orquestração de microsserviços |
| **HTTPX** | Requisições assíncronas entre serviços |

---

## 🔍 Considerações Finais
O projeto demonstra uma integração prática entre **IA generativa** e **processamento de áudio**, com foco em **modularidade**, **escalabilidade** e **clareza arquitetural**.  
A abordagem baseada em microsserviços garante independência entre componentes, facilitando futuras expansões — como **vetorização**, **cache semântico** ou **autenticação**.
