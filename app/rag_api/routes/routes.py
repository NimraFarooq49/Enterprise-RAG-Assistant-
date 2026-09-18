from fastapi import APIRouter, UploadFile, File
from app.rag_api.models.response import Response
from app.rag_api.models.schemas import (
    DocumentResponse,
    SearchRequest,
    SearchResult,
    ChatRequest,
    ChatResult,
)
from app.rag_api.services.services import (
    upload_documents,
    get_all_documents,
    get_document_by_id,
    delete_document,
    health_check,
    search_documents,
    chat_documents,
)

router = APIRouter(tags=["RAG API"])


@router.post(
    "/documents/upload",
    response_model=Response[list[DocumentResponse]],
    status_code=201,
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["files"],
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "format": "binary",
                                },
                            }
                        },
                    }
                }
            }
        }
    },
)
def document_upload(files: list[UploadFile] = File(...)):
    return upload_documents(files)


@router.get(
    "/documents",
    response_model=Response[list[DocumentResponse]],
)
def get_documents():
    return get_all_documents()


@router.get(
    "/documents/{document_id}",
    response_model=Response[DocumentResponse],
)
def get_document(document_id: int):
    return get_document_by_id(document_id)


@router.delete(
    "/documents/{document_id}",
    response_model=Response[None],
)
def remove_document(document_id: int):
    return delete_document(document_id)


@router.get("/health")
def health():
    return health_check()


@router.post(
    "/search",
    response_model=Response[list[SearchResult]],
)
def search(request: SearchRequest):
    return search_documents(
        request.query,
        request.limit,
    )


@router.post(
    "/chat",
    response_model=Response[ChatResult],
)
def chat(request: ChatRequest):
    return chat_documents(request.query)
