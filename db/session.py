from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL",
    'DATABASE_URL')

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=True)

print("Connecting to:", DATABASE_URL)
# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)