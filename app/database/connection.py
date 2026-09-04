from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = "sqlite:///./enterprise_rag.db"

try:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    with engine.connect():
        print("Database connection successful")

except SQLAlchemyError as e:
    print(f"Database error: {e}")
    raise

except Exception as e:
    print(f"Unexpected database error: {e}")
    raise


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
