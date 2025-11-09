from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
import os
from dotenv import load_dotenv

load_dotenv()

# Данные подключения к БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pediatric_user:intb958@localhost/pediatric_crm")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Создает таблицы, если они не существуют"""
    Base.metadata.create_all(bind=engine)