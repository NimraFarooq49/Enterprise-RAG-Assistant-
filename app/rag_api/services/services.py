import os
import json
import re
import ollama
from fastapi import UploadFile, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database.connection import SessionLocal
from app.database.models import Document
from app.rag_api.models.response import Response
from app.rag_api.models.schemas import (
    DocumentResponse,
    SearchResult,
    ChatResult,
    ChatSource,
)
from app.ingestion.loader import load_document
from app.ingestion.cleaner import clean_text
from app.ingestion.chunker import chunk_text
from app.ingestion.embedder import create_embedding
from app.vectorstore.qdrant_connection import (
    client,
    COLLECTION_NAME,
    store_chunks,
    search_chunks,
)
from qdrant_client.models import Filter, FieldCondition, MatchValue

UPLOAD_FOLDER = "data/documents"
ALLOWED_TYPES = [".pdf", ".txt", ".md"]


def upload_documents(files: list[UploadFile]):

    db = SessionLocal()
    uploaded_documents = []

    try:

        if not files:
            raise HTTPException(
                status_code=400,
                detail="At least one document is required",
            )

        if not os.path.isdir(UPLOAD_FOLDER):
            raise HTTPException(
                status_code=404,
                detail="File upload path not found",
            )

        for file in files:

            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="File name is missing",
                )

            extension = os.path.splitext(file.filename)[1].lower()

            if extension not in ALLOWED_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename}: Only PDF, TXT and Markdown files are allowed",
                )

            file_path = os.path.join(
                UPLOAD_FOLDER,
                file.filename,
            )

            if os.path.exists(file_path):
                raise HTTPException(
                    status_code=409,
                    detail=f"{file.filename}: File already exists",
                )

            file_data = file.file.read()

            if not file_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename}: File is empty",
                )

            with open(file_path, "wb") as f:
                f.write(file_data)

            # 1. LOAD DOCUMENT

            document_pages = load_document(file_path)

            if not document_pages:

                if os.path.exists(file_path):
                    os.remove(file_path)

                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename}: Could not extract text from document",
                )

            # 2. CLEAN TEXT
            cleaned_pages = []

            for page in document_pages:

                content_type = page.get(
                    "content_type",
                    "text",
                )

                cleaned_text = clean_text(page.get("text", ""))

                if cleaned_text:

                    cleaned_pages.append(
                        {
                            "page_number": page.get("page_number"),
                            "section": page.get("section"),
                            "content_type": content_type,
                            "text": cleaned_text,
                        }
                    )

            if not cleaned_pages:

                if os.path.exists(file_path):
                    os.remove(file_path)

                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename}: No usable text found in document",
                )

            document = Document(
                file_name=file.filename,
                file_type=extension,
            )

            db.add(document)
            db.flush()

            # 4. CREATE CHUNKS
            chunks = chunk_text(
                cleaned_pages,
                document.document_id,
                file.filename,
            )

            if not chunks:

                if os.path.exists(file_path):
                    os.remove(file_path)

                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename}: Could not create document chunks",
                )

            # 5. CREATE EMBEDDINGS
            for chunk in chunks:

                embedding = create_embedding(chunk["text"])
                chunk["embedding"] = embedding

            store_chunks(chunks)

            # 7. UPDATE DOCUMENT INFO
            document.number_of_chunks = len(chunks)
            document.processing_status = "completed"

            uploaded_documents.append(DocumentResponse.model_validate(document))

        db.commit()

        return Response(
            status_code=201,
            message="Documents uploaded, processed, embedded and stored successfully",
            data=uploaded_documents,
        )

    except HTTPException:

        db.rollback()
        raise

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error while uploading documents",
        )

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Document upload failed",
        )

    finally:

        db.close()


def get_all_documents():
    db = SessionLocal()

    try:
        documents = db.query(Document).all()

        data = [DocumentResponse.model_validate(document) for document in documents]

        return Response(
            status_code=200,
            message="Documents retrieved successfully",
            data=data,
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error while fetching documents",
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch documents",
        )

    finally:
        db.close()


def get_document_by_id(document_id: int):
    db = SessionLocal()

    try:
        document = (
            db.query(Document).filter(Document.document_id == document_id).first()
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        data = DocumentResponse.model_validate(document)

        return Response(
            status_code=200,
            message="Document retrieved successfully",
            data=data,
        )

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error while fetching document",
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to fetch document",
        )

    finally:
        db.close()


def delete_document(document_id: int):
    db = SessionLocal()

    try:
        # Find document in SQLite
        document = (
            db.query(Document).filter(Document.document_id == document_id).first()
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
            wait=True,
        )

        file_path = os.path.join(
            UPLOAD_FOLDER,
            document.file_name,
        )

        if os.path.exists(file_path):
            os.remove(file_path)

        db.delete(document)
        db.commit()

        return Response(
            status_code=200,
            message="Document and all related data deleted successfully",
            data=None,
        )

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error while deleting document",
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to delete document and related data",
        )

    finally:
        db.close()


def health_check():
    db = SessionLocal()

    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "message": "API and database are working successfully",
        }

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Health check failed",
        )

    finally:
        db.close()


def _tokenize(text: str):
    return set(
        re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text.lower(),
        )
    )


def _keyword_score(query: str, text: str):
    query_words = _tokenize(query)
    text_words = _tokenize(text)

    if not query_words:
        return 0.0

    matched_words = query_words.intersection(text_words)

    word_score = len(matched_words) / len(query_words)

    query_text = query.lower().strip()
    text_lower = text.lower()

    phrase_score = 1.0 if query_text in text_lower else 0.0

    return max(
        word_score,
        phrase_score,
    )


def search_documents(query: str, limit: int = 10):
    if not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query is required",
        )

    query_vector = create_embedding(query)

    results = search_chunks(
        query_vector,
        limit=max(limit * 2, 20),
        score_threshold=0.30,
    )

    if not results:
        return Response(
            status_code=200,
            message=("I could not find this information " "in the uploaded documents."),
            data=[],
        )

    ranked_results = []

    for result in results:
        payload = result.payload or {}

        text = payload.get(
            "text",
            "",
        ).strip()

        if not text:
            continue

        semantic_score = float(result.score or 0.0)

        keyword_score = _keyword_score(
            query,
            text,
        )

        final_score = semantic_score * 0.70 + keyword_score * 0.30

        ranked_results.append(
            {
                "result": result,
                "final_score": final_score,
                "keyword_score": keyword_score,
            }
        )

    ranked_results.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    if not ranked_results:
        return Response(
            status_code=200,
            message=("I could not find this information " "in the uploaded documents."),
            data=[],
        )

    # Primary document select karein
    top_score = ranked_results[0]["final_score"]

    top_payload = ranked_results[0]["result"].payload or {}

    primary_document_id = top_payload.get("document_id")

    selected_results = []

    for item in ranked_results:
        item_payload = item["result"].payload or {}

        item_document_id = item_payload.get("document_id")

        final_score = item["final_score"]
        keyword_score = item["keyword_score"]

        same_document = item_document_id == primary_document_id

        exceptionally_relevant_other_document = (
            final_score >= top_score - 0.05 and keyword_score >= 0.45
        )

        if same_document or exceptionally_relevant_other_document:
            selected_results.append(item)

    selected_results = selected_results[:limit]

    if not selected_results:
        return Response(
            status_code=200,
            message=("I could not find this information " "in the uploaded documents."),
            data=[],
        )

    data = []

    for item in selected_results:
        result = item["result"]
        payload = result.payload or {}

        data.append(
            SearchResult(
                document_id=payload.get("document_id"),
                file_name=payload.get(
                    "file_name",
                    "Unknown document",
                ),
                chunk_number=payload.get("chunk_number"),
                page_number=payload.get("page_number"),
                text=payload.get(
                    "text",
                    "",
                ),
                score=round(
                    item["final_score"],
                    4,
                ),
            )
        )

    return Response(
        status_code=200,
        message="Search completed successfully",
        data=data,
    )


def chat_documents(query: str):
    fallback_msg = "I could not find this information in the uploaded documents."

    # print("[CHAT] FINAL CHAT FUNCTION LOADED")

    # 1. Validate query
    if not isinstance(query, str) or not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query is required",
        )

    query = query.strip()

    # 2. Query embedding
    query_vector = create_embedding(query)

    # 3. Retrieve broad candidate set
    results = search_chunks(
        query_vector=query_vector,
        limit=40,
        score_threshold=None,
    )

    # print(
    # "[CHAT] Retrieved count:",
    # len(results),
    # )

    if not results:
        return Response(
            status_code=200,
            message="Chat completed successfully",
            data=ChatResult(
                answer=fallback_msg,
                sources=[],
            ),
        )

    ranked_results = []

    for result in results:
        payload = result.payload or {}

        text = payload.get(
            "text",
            "",
        ).strip()

        if not text:
            continue

        content_type = payload.get(
            "content_type",
            "text",
        )

        if content_type not in [
            "text",
            "table",
        ]:
            continue

        semantic_score = float(result.score or 0.0)

        keyword_score = _keyword_score(
            query,
            text,
        )

        final_score = semantic_score * 0.70 + keyword_score * 0.30

        ranked_results.append(
            {
                "result": result,
                "final_score": final_score,
                "keyword_score": keyword_score,
            }
        )

    ranked_results.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    if not ranked_results:
        return Response(
            status_code=200,
            message="Chat completed successfully",
            data=ChatResult(
                answer=fallback_msg,
                sources=[],
            ),
        )

    # 5. Select top relevant chunks
    selected_items = ranked_results[:8]

    print(
        "[CHAT] Selected chunks:",
        len(selected_items),
    )

    if not selected_items:
        return Response(
            status_code=200,
            message="Chat completed successfully",
            data=ChatResult(
                answer=fallback_msg,
                sources=[],
            ),
        )

    # 6. Build context
    context_parts = []
    source_map = {}
    seen_chunks = set()
    source_counter = 1
    context_length = 0
    max_context_length = 9000

    for item in selected_items:
        result = item["result"]

        payload = result.payload or {}

        text = payload.get(
            "text",
            "",
        ).strip()

        if not text:
            continue

        content_type = payload.get(
            "content_type",
            "text",
        )

        document_id = payload.get("document_id")

        chunk_number = payload.get("chunk_number")

        chunk_key = (
            document_id,
            chunk_number,
            content_type,
        )

        if chunk_key in seen_chunks:
            continue

        seen_chunks.add(chunk_key)

        file_name = payload.get(
            "file_name",
            "Unknown document",
        )

        page_number = payload.get("page_number")

        source_id = f"SOURCE_{source_counter}"

        source_counter += 1

        context_block = (
            f"[{source_id}]\n"
            f"Document: {file_name}\n"
            f"Page: {page_number}\n"
            f"Chunk: {chunk_number}\n"
            f"Content Type: {content_type}\n"
            f"Content:\n{text}"
        )

        if context_length + len(context_block) > max_context_length:
            continue

        source_map[source_id] = {
            "file_name": file_name,
            "page_number": page_number,
        }

        context_parts.append(context_block)

        context_length += len(context_block)

    if not context_parts:
        return Response(
            status_code=200,
            message="Chat completed successfully",
            data=ChatResult(
                answer=fallback_msg,
                sources=[],
            ),
        )

    context = "\n\n".join(context_parts)

    print(
        "[CHAT] Final context length:",
        len(context),
    )

    print(
        "[CHAT] Final context chunks:",
        len(context_parts),
    )

    # Diagnostic log
    # print("========== FINAL CONTEXT SENT TO LLM ==========")
    # print(context)
    # print("================================================")

    # 7. Grounded LLM prompt
    prompt = f"""
You are an Enterprise RAG Assistant.

Answer the user's question using ONLY the document information
provided below.

STRICT RULES:

1. Do not use outside knowledge.

2. Do not guess or invent information.

3. If the answer is not available in the document information,
return exactly:

I could not find this information in the uploaded documents.

4. If the user asks for a list, include every supported item.

5. If the information comes from a table, preserve every row exactly.

6. Never mix values from different rows.

7. For every table row, preserve the relationship between:
Area, Preferred Option, and Reason.

8. Do not add technologies, areas, or reasons that are not present
in the document information.

9. Do not add OpenAI, Azure OpenAI, NLP, Machine Learning,
Cloud Deployment, or any other outside information unless it is
explicitly present in the document information.

10. The answer must be a natural-language answer.

11. The JSON object must contain ONLY these two keys:
answer and source_ids.

12. Never use any other key such as:
preferred_technology_options,
technology,
areas, or reasons.

13. Return valid JSON only in this exact format:

{{
    "answer": "complete answer here",
    "source_ids": ["SOURCE_1"]
}}

DOCUMENT INFORMATION:

{context}

USER QUESTION:

{query}
"""

    # 8. Generate answer
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        format="json",
        options={
            "temperature": 0,
            "num_ctx": 8192,
            "num_predict": 1200,
        },
    )

    raw_answer = response.get("message", {}).get("content", "").strip()

    # print(
    # "[CHAT] Raw LLM answer:",
    # raw_answer,
    # )

    # 9. Parse JSON
    answer = ""
    selected_source_ids = []

    try:
        llm_result = json.loads(raw_answer)
        possible_answer = llm_result.get("answer")
        possible_source_ids = llm_result.get(
            "source_ids",
            [],
        )

        if isinstance(
            possible_answer,
            str,
        ):
            answer = possible_answer.strip()

        if isinstance(
            possible_source_ids,
            list,
        ):
            selected_source_ids = possible_source_ids

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        answer = ""
        selected_source_ids = []

    # 10. Final fallback
    if not answer:
        answer = fallback_msg
        selected_source_ids = []

    # 11. Convert source IDs to API sources
    sources = []

    if answer != fallback_msg:
        for source_id in selected_source_ids:

            source_info = source_map.get(source_id)

            if not source_info:
                continue

            source = ChatSource(
                file_name=source_info["file_name"],
                page_number=source_info["page_number"],
            )

            if source not in sources:
                sources.append(source)

    # 12. Safe source fallback
    if not sources and answer != fallback_msg:
        first_payload = ranked_results[0]["result"].payload or {}

        fallback_source = ChatSource(
            file_name=first_payload.get(
                "file_name",
                "Unknown document",
            ),
            page_number=first_payload.get("page_number"),
        )

        sources.append(fallback_source)

    # 13. Final response
    return Response(
        status_code=200,
        message="Chat completed successfully",
        data=ChatResult(
            answer=answer,
            sources=sources,
        ),
    )
