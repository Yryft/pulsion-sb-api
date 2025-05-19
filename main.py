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
        "http://192.168.0.160:3000",
        "https://bazaar-data.up.railway.app"   # your deployed frontend
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
        'latest':  timedelta(hours=2),
        'all':     None
    }
    return mapping.get(range_str)

# --- Helper to apply time filters ---
def apply_time_filters(query, timestamp_field, start: Optional[datetime], end: Optional[datetime]):
    if start:
        query = query.filter(timestamp_field >= start)
    if end:
        query = query.filter(timestamp_field <= end)
    return query

# --- Time series bazaar price endpoint ---
@app.get("/prices/{item_id}", summary="Time series bazaar sell prices")
def get_prices(
    item_id: str,
    range: str = Query(
        '1week',
        description="Time window: all,6months,2months,1week,1day,latest"
    ),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Returns time series of Bazaar sell prices for a given item.
    """
    now = datetime.now(timezone.utc)
    td = parse_range(range)
    start = None if range == 'all' or td is None else now - td

    q = db.query(
        Bazaar.timestamp,
        Bazaar.data['sellPrice'].as_float().label('price')
    ).filter(Bazaar.product_id == item_id)
    q = apply_time_filters(q, Bazaar.timestamp, start, now)
    rows = q.order_by(Bazaar.timestamp).all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No bazaar price data for item {item_id}")

    return [{"timestamp": ts.isoformat(), "price": price} for ts, price in rows]

# --- Latest sold volume endpoint --- (Bazaar only)
@app.get("/sold/{item_id}", summary="Latest amount sold in a week")
def get_bazaar_sold(
    item_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns the most recent moving sold volume (sellMovingWeek) for the given item.
    """
    latest = (
        db.query(
            Bazaar.timestamp,
            Bazaar.data['sellMovingWeek'].as_float().label('volume')
        )
        .filter(Bazaar.product_id == item_id)
        .order_by(Bazaar.timestamp.desc())
        .first()
    )

    if not latest:
        raise HTTPException(status_code=404, detail=f"No bazaar sold data for item {item_id}")

    ts, vol = latest
    return {
        "item_id": item_id,
        "timestamp": ts.isoformat(),
        "sold_moving_week": vol,
    }

# --- Elections endpoint ---
@app.get("/elections", summary="List mayoral elections")
def get_elections(
    range: str = Query(
        '1week',
        description="Time window: all,6months,2months,1week,1day,latest"
    ),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Returns list of elections with year, mayor, and timestamp within the specified time window.
    """
    now = datetime.now(timezone.utc)
    td = parse_range(range)
    start = None if range == 'all' or td is None else now - td

    q = db.query(
        Election.year,
        Election.mayor,
        Election.timestamp
    )
    q = apply_time_filters(q, Election.timestamp, start, now)
    rows = q.order_by(Election.timestamp).all()

    return [
        {"year": year, "mayor": mayor, "timestamp": ts.isoformat()}
        for year, mayor, ts in rows
    ]

# --- Items list endpoint ---
@app.get("/items", summary="Aggregate tracked item IDs")
def list_items(db: Session = Depends(get_db)) -> List[str]:
    baz_ids = db.query(Bazaar.product_id).distinct().all()
    return sorted({i[0] for i in baz_ids})
