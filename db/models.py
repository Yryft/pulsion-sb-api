from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base
from db.session import engine

Base = declarative_base()

class AuctionsSold(Base):
    __tablename__ = 'auctions_sold'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    data = Column(JSON)

class AuctionsLB(Base):
    __tablename__ = 'auctions_lb'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    data = Column(JSON)

class Bazaar(Base):
    __tablename__ = 'bazaar'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    data = Column(JSON)

class Firesale(Base):
    __tablename__ = 'firesales'
    item_id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    data = Column(JSON)

class Election(Base):
    __tablename__ = 'elections'
    year = Column(Integer, primary_key=True, index=True)
    mayor = Column(String)
    timestamp = Column(DateTime)

class ItemSale(Base):
    __tablename__ = 'item_sales'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(String, index=True)
    count = Column(Integer)
    timestamp = Column(DateTime, index=True)