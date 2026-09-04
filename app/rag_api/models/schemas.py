from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    document_id: int
    file_name: str
    file_type: str
    upload_time: datetime
    number_of_chunks: int
    processing_status: str

    model_config = ConfigDict(from_attributes=True)
