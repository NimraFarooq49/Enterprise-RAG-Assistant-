# import ollama
# def create_embedding(text: str):
#     response = ollama.embeddings(model="nomic-embed-text", prompt=text)
#     return response["embedding"]
import os
import requests


def create_embedding(text: str):
    headers = {
        "Authorization": f"Bearer {os.getenv('JINA_API_KEY')}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "jina-embeddings-v3",
        "input": [text],
        "task": "retrieval.passage",
        "dimensions": 768,
    }

    response = requests.post(
        "https://api.jina.ai/v1/embeddings",
        headers=headers,
        json=data,
        timeout=60,
    )

    response.raise_for_status()

    result = response.json()

    return result["data"][0]["embedding"]
