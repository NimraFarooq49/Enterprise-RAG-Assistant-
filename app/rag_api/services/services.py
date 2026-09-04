import os
from fastapi import UploadFile, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database.connection import SessionLocal
from app.database.models import Document
from app.rag_api.models.response import Response
from app.rag_api.models.schemas import DocumentResponse
from app.ingestion.loader import load_document

UPLOAD_FOLDER = "data/documents"

ALLOWED_TYPES = [".pdf", ".txt", ".md"]


def upload_document(file: UploadFile):

    db = SessionLocal()

    try:

        extension = os.path.splitext(file.filename)[1].lower()

        if extension not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400, detail="Only PDF, TXT and Markdown files are allowed"
            )

        if not os.path.isdir(UPLOAD_FOLDER):
            raise HTTPException(status_code=404, detail="File upload path not found")

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

        if os.path.exists(file_path):
            raise HTTPException(status_code=409, detail="File already exists")

        file_data = file.file.read()

        if not file_data:
            raise HTTPException(status_code=400, detail="File is empty")
        with open(file_path, "wb") as f:
            f.write(file_data)

        # Extract text from document
        text = load_document(file_path)

        if not text.strip():
            raise HTTPException(
                status_code=400, detail="Could not extract text from document"
            )

        document = Document(file_name=file.filename, file_type=extension)

        db.add(document)
        db.commit()
        db.refresh(document)

        data = DocumentResponse.model_validate(document)

        return Response(
            status_code=201,
            message="Document uploaded and text extracted successfully",
            data=data,
        )

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=500, detail="Database error while uploading document"
        )

    except Exception:
        db.rollback()

        raise HTTPException(status_code=500, detail="Document upload failed")

    finally:
        db.close()


def get_all_documents():
    db = SessionLocal()

    try:
        documents = db.query(Document).all()

        data = [DocumentResponse.model_validate(document) for document in documents]

        return Response(
            status_code=200, message="Documents retrieved successfully", data=data
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Database error while fetching documents"
        )

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to fetch documents")

    finally:
        db.close()


def delete_document(document_id: int):
    db = SessionLocal()

    try:
        document = (
            db.query(Document).filter(Document.document_id == document_id).first()
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        file_path = os.path.join(UPLOAD_FOLDER, document.file_name)

        if os.path.exists(file_path):
            os.remove(file_path)

        db.delete(document)
        db.commit()

        return Response(
            status_code=200, message="Document deleted successfully", data=None
        )

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Database error while deleting document"
        )

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete document")

    finally:
        db.close()


def health_check():

    db = SessionLocal()

    try:
        # Check database connection
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "message": "API and database are working successfully",
        }

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(status_code=503, detail="Database connection failed")

    except Exception:
        raise HTTPException(status_code=500, detail="Health check failed")

    finally:
        db.close()
