from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    document_id: int
    file_name: str
    file_type: str
    upload_time: datetime
    number_of_chunks: int
    processing_status: str

    model_config = ConfigDict(from_attributes=True)


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class SearchResult(BaseModel):
    document_id: int
    file_name: str
    chunk_number: int
    page_number: int | None = None
    text: str
    score: float


class ChatRequest(BaseModel):
    query: str


class ChatSource(BaseModel):
    file_name: str
    page_number: int | None = None


class ChatResult(BaseModel):
    answer: str
    sources: list[ChatSource] = Field(default_factory=list)
