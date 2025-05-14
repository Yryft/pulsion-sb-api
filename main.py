from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from db.session import SessionLocal
from db.models import AuctionsLB

app = FastAPI(title="SkyBlock Auction Analytics")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/items", summary="List all tracked item IDs")
def list_items(db: Session = Depends(get_db)) -> List[str]:
    # return distinct product_ids
    ids = db.query(AuctionsLB.product_id).distinct().all()
    return [i[0] for i in ids]

@app.get("/prices/{item_id}", summary="Time series for an item")
def get_prices(
    item_id: str,
    start: datetime = Query(None),
    end:   datetime = Query(None),
    db:    Session  = Depends(get_db)
):
    q = db.query(AuctionsLB.timestamp, AuctionsLB.data["starting_bid"].as_float().label("price"))\
          .filter(AuctionsLB.product_id == item_id)\
          .order_by(AuctionsLB.timestamp)
    if start:
        q = q.filter(AuctionsLB.timestamp >= start)
    if end:
        q = q.filter(AuctionsLB.timestamp <= end)
    rows = q.all()
    if not rows:
        raise HTTPException(404, f"No data for item {item_id}")
    return [{"timestamp": ts.isoformat(), "price": price} for ts, price in rows]

@app.get("/stats/{item_id}", summary="Summary statistics for an item")
def get_stats(item_id: str, db: Session = Depends(get_db)):
    sub = db.query(
        func.min(AuctionsLB.data["starting_bid"].as_float()).label("min_price"),
        func.max(AuctionsLB.data["starting_bid"].as_float()).label("max_price"),
        func.avg(AuctionsLB.data["starting_bid"].as_float()).label("avg_price"),
        func.count().label("samples")
    ).filter(AuctionsLB.product_id == item_id)
    stats = sub.one()
    if stats.samples == 0:
        raise HTTPException(404, f"No data for item {item_id}")
    return {
        "min_price": stats.min_price,
        "max_price": stats.max_price,
        "avg_price": round(stats.avg_price, 2),
        "samples":   stats.samples
    }

@app.get("/compare", summary="Compare multiple items")
def compare(
    items: List[str] = Query(..., description="Comma-separated item IDs"),
    db:    Session  = Depends(get_db)
):
    # Return a dict of item_id -> time-series
    result = {}
    for item in items:
        rows = db.query(AuctionsLB.timestamp, AuctionsLB.data["starting_bid"].as_float().label("price"))\
                 .filter(AuctionsLB.product_id == item)\
                 .order_by(AuctionsLB.timestamp).all()
        result[item] = [{"timestamp": ts.isoformat(), "price": p} for ts, p in rows]
    return result
