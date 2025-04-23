import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional, List
from datetime import datetime

# Lade Umgebungsvariablen aus .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def get_db() -> Session:
    with Session(engine) as session:
        yield session
