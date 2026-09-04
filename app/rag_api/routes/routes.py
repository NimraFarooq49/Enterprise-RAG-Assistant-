from fastapi import APIRouter, UploadFile, File
from app.rag_api.models.response import Response
from app.rag_api.models.schemas import DocumentResponse
from app.rag_api.services.services import (
    upload_document,
    get_all_documents,
    delete_document,
    health_check,
)

router = APIRouter(tags=["RAG API"])


@router.post(
    "/documents/upload",
    response_model=Response[DocumentResponse],
    status_code=201,
)
def document_upload(file: UploadFile = File(...)):
    return upload_document(file)


@router.get("/documents", response_model=Response[list[DocumentResponse]])
def get_documents():
    return get_all_documents()


@router.delete("/documents/{document_id}", response_model=Response[None])
def delete_document_by_id(document_id: int):
    return delete_document(document_id)


@router.get("/health")
def check_health():
    return health_check()
