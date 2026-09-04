from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .connection import Base


class Document(Base):
    __tablename__ = "documents"

    document_id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    number_of_chunks = Column(Integer, default=0)
    processing_status = Column(String, default="uploaded")
    upload_time = Column(DateTime, default=datetime.utcnow)
