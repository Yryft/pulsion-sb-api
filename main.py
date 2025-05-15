from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from db.session import SessionLocal
from db.models import AuctionsLB, Bazaar, Firesale, ItemSale, Election

app = FastAPI(title="SkyBlock Analytics")

# --- Root helper endpoint ---
@app.get("/", include_in_schema=False)
def root() -> Dict[str, Any]:
    """
    Basic API information and available routes.
    """
    return {
        "message": "Welcome to the SkyBlock Analytics API.",
        "usage": {
            "/items": "List all tracked item IDs (Bazaar & BIN)",
            "/prices/{item_id}?range=...": "Time series price (BIN or Bazaar) with optional range: all,6months,2months,1week,1day,1hour (default 1week)",
            "/firesales?range=...": "List firesale events with optional range",
            "/item_sales?range=...": "List raw item sales records with optional range",
            "/elections?range=...": "List mayoral elections with optional range",
            "/docs": "Interactive Swagger UI",
            "/redoc": "ReDoc documentation",
            "/openapi.json": "OpenAPI schema JSON"
        }
    }

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
    q1 = db.query(
        AuctionsLB.timestamp,
        AuctionsLB.data['starting_bid'].as_float().label('price')
    ).filter(AuctionsLB.product_id == item_id)
    q1 = apply_time_filters(q1, AuctionsLB.timestamp, start, now)
    rows = q1.order_by(AuctionsLB.timestamp).all()
    if rows:
        return [{"timestamp": ts.isoformat(), "price": price} for ts, price in rows]
    # Fallback to Bazaar
    q2 = db.query(
        Bazaar.timestamp,
        Bazaar.data['sell_price'].as_float().label('price')
    ).filter(Bazaar.product_id == item_id)
    q2 = apply_time_filters(q2, Bazaar.timestamp, start, now)
    rows2 = q2.order_by(Bazaar.timestamp).all()
    if rows2:
        return [{"timestamp": ts.isoformat(), "price": price} for ts, price in rows2]
    raise HTTPException(status_code=404, detail=f"No price data for item {item_id}")

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

# Firesales
generic_list(
    Firesale.timestamp,
    [Firesale.item_id, Firesale.timestamp],
    path="/firesales",
    summary="List firesale events"
)

# Item sales
generic_list(
    ItemSale.timestamp,
    [ItemSale.item_id, ItemSale.count, ItemSale.timestamp],
    path="/item_sales",
    summary="Raw item sales records"
)

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
    lb_ids  = db.query(AuctionsLB.product_id).distinct().all()
    return sorted({i[0] for i in baz_ids + lb_ids})
