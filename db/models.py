from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base
from db.session import engine

Base = declarative_base()

class Bazaar(Base):
    __tablename__ = 'bazaar'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    data = Column(JSON)
    
class Election(Base):
    __tablename__ = 'elections'
    year = Column(Integer, primary_key=True, index=True)
    mayor = Column(String)
    timestamp = Column(DateTime)