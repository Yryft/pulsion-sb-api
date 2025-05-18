from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from db.session import SessionLocal
from db.models import Bazaar, Election

app = FastAPI(title="SkyBlock Analytics")

# ─── Enable CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",                    # your Next.js dev URL
        "https://https://bazaar-data.up.railway.app"   # your deployed frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)
# ────────────────────────────────────────────────────────────────────────────────

# --- DB Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helper: map range string to timedelta ---
def parse_range(range_str: str) -> Optional[timedelta]:
    mapping = {
        '6months': timedelta(days=180),
        '2months': timedelta(days=60),
        '1week':   timedelta(weeks=1),
        '1day':    timedelta(days=1),
        '1hour':   timedelta(hours=1)
    }
    return mapping.get(range_str)

# --- Helper to apply time filters ---
def apply_time_filters(query, timestamp_field, start: Optional[datetime], end: Optional[datetime]):
    if start:
        query = query.filter(timestamp_field >= start)
    if end:
        query = query.filter(timestamp_field <= end)
    return query

# --- Combined prices endpoint ---
@app.get("/prices/{item_id}", summary="Time series price for BIN or Bazaar")
def get_prices(
    item_id: str,
    range: str = Query('1week', description="Time window: all,6months,2months,1week,1day,1hour"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Returns time series of prices: BIN (auctions) or Bazaar (sell_price).
    Chooses AuctionsLB if any BIN data exists, otherwise Bazaar.
    """
    now = datetime.now(timezone.utc)
    td = parse_range(range)
    start = None if range == 'all' or td is None else now - td
    # First try AuctionsLB
    # Fallback to Bazaar
    q2 = db.query(
        Bazaar.timestamp,
        Bazaar.data.label('data')
    ).filter(Bazaar.product_id == item_id)
    q2 = apply_time_filters(q2, Bazaar.timestamp, start, now)
    rows2 = q2.order_by(Bazaar.timestamp).all()
    if rows2:
        return [{"timestamp": ts.isoformat(), "price": price} for ts, price in rows2]
    raise HTTPException(status_code=404, detail=f"No price data for item {item_id}")

# --- Sold volume endpoint --- (Bazaar only for now)
@app.get("/sold/{item_id}", summary="Amount sold in the given time range")
def get_bazaar_sold(
    item_id: str,
    range: str = Query('1week', description="Time window: all,6months,2months,1week,1day,1hour"),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    td = parse_range(range)
    start = None if range == 'all' or td is None else now - td

    q = db.query(
        Bazaar.timestamp,
        Bazaar.data['sellMovingWeek'].as_float().label('volume')
    ).filter(Bazaar.product_id == item_id)
    
    q = apply_time_filters(q, Bazaar.timestamp, start, now)
    rows = q.order_by(Bazaar.timestamp).all()

    if not rows or len(rows) < 2:
        raise HTTPException(status_code=404, detail=f"Not enough data to compute sold volume for item {item_id}")

    sold_amount = rows[-1].volume - rows[0].volume
    return {
        "item_id": item_id,
        "range": range,
        "sold": sold_amount,
        "from": rows[0].timestamp.isoformat(),
        "to": rows[-1].timestamp.isoformat()
    }


# --- Generic list endpoint factory ---
def generic_list(
    timestamp_field,
    fields: List[Any],
    path: str,
    summary: str
):
    @app.get(path, summary=summary)
    def endpoint(
        range: str = Query('1week', description="Time window: all,6months,2months,1week,1day,1hour"),
        db: Session = Depends(get_db)
    ):
        now = datetime.now(timezone.utc)
        td = parse_range(range)
        start = None if range == 'all' or td is None else now - td
        q = db.query(*fields)
        q = apply_time_filters(q, timestamp_field, start, now)
        rows = q.order_by(timestamp_field).all()
        return [dict(zip(
            [f.key if hasattr(f, 'key') else f.name for f in fields], r
        )) for r in rows]
    return endpoint

# Elections
generic_list(
    Election.timestamp,
    [Election.year, Election.mayor, Election.timestamp],
    path="/elections",
    summary="List mayoral elections"
)

# Items list remains unchanged
@app.get("/items", summary="Aggregate tracked item IDs")
def list_items(db: Session = Depends(get_db)) -> List[str]:
    baz_ids = db.query(Bazaar.product_id).distinct().all()
    return sorted({i[0] for i in baz_ids})
