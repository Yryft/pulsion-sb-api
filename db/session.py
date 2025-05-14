from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL",
    'postgresql://postgres:cFwXnePinMlwySESPTqigzWzqeAHKcVt@switchyard.proxy.rlwy.net:41004/railway')

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=True)
# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)