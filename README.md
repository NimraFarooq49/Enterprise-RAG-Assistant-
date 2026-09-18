# Enterprise RAG Assistant

A document-based RAG API that allows users to upload documents and ask questions based on their content.

## Features

- PDF, TXT, and Markdown support
- PDF table extraction
- Document chunking and embeddings
- Qdrant vector search
- Semantic + keyword retrieval
- Chat with document sources
- Fallback for unavailable information

## Tech Stack

- Python
- FastAPI
- Qdrant
- Sentence Transformers
- Ollama / LLM
- SQLite

## Run

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`
