from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "documents"


client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
)


def create_collection():
    collections = client.get_collections()

    if COLLECTION_NAME not in [
        collection.name for collection in collections.collections
    ]:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE,
            ),
        )

        print("Collection created successfully")

    else:
        print("Collection already exists")


def store_chunks(chunks):
    points = []

    for chunk in chunks:
        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=chunk["embedding"],
                payload={
                    "document_id": chunk["document_id"],
                    "file_name": chunk["file_name"],
                    "chunk_number": chunk["chunk_number"],
                    "page_number": chunk["page_number"],
                    "content_type": chunk["content_type"],
                    "text": chunk["text"],
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    print(f"{len(points)} chunks stored in Qdrant")


def search_chunks(
    query_vector,
    limit=40,
    score_threshold=None,
):
    search_arguments = {
        "collection_name": COLLECTION_NAME,
        "query": query_vector,
        "limit": limit,
        "with_payload": True,
        "with_vectors": False,
    }

    # Chat ke liye threshold optional rakha gaya hai.
    # Isse relevant table chunk accidentally remove nahi hoga.
    if score_threshold is not None:
        search_arguments["score_threshold"] = score_threshold

    results = client.query_points(**search_arguments)

    return results.points


if __name__ == "__main__":
    create_collection()
