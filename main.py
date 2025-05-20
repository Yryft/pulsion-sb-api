from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from db.session import SessionLocal
from db.models import Bazaar, Election

# Adjust this factor to scale volume impact in your profitability formula
# tweak these as you like
CAPITAL = 1_000_000_000       # 1 billion coins bankroll
MARKET_SHARE = 0.10          # assume you can capture 10% of weekly volume
SCALING_FACTOR = 1           # keep revenue in raw coins

app = FastAPI(title="SkyBlock Analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.0.160:3000",
        "https://bazaar-data.up.railway.app",
        "https://pulsion-apiv1.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def parse_range(r: str) -> Optional[timedelta]:
    m = {
        '6months': timedelta(days=180),
        '2months': timedelta(days=60),
        '1week':   timedelta(weeks=1),
        '1day':    timedelta(days=1),
        'latest':  timedelta(hours=2),
        'all':     None
    }
    return m.get(r)


def apply_time_filters(q, field, start, end):
    if start:
        q = q.filter(field >= start)
    if end:
        q = q.filter(field <= end)
    return q


@app.get("/prices/{item_id}", summary="Time series bazaar data")
def get_prices(
    item_id: str,
    range: str = Query('1week', description="all,6months,2months,1week,1day,latest"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    td = parse_range(range)
    start = None if range == 'all' or td is None else now - td

    q = db.query(Bazaar.timestamp, Bazaar.data.label('data'))
    q = q.filter(Bazaar.product_id == item_id)
    q = apply_time_filters(q, Bazaar.timestamp, start, now)
    rows = q.order_by(Bazaar.timestamp).all()

    if not rows:
        raise HTTPException(404, f"No bazaar data for item {item_id}")

    return [{"timestamp": ts.isoformat(), "data": data} for ts, data in rows]


@app.get("/sold/{item_id}", summary="Latest Bazaar summary data")
def get_bazaar_sold(item_id: str, db: Session = Depends(get_db)):
    latest = (
        db.query(Bazaar.data.label('data'))
          .filter(Bazaar.product_id == item_id)
          .order_by(Bazaar.timestamp.desc())
          .first()
    )
    if not latest:
        raise HTTPException(404, f"No bazaar data for item {item_id}")
    return latest.data


class ItemProfit(BaseModel):
    item_id: str
    sell_price: float
    buy_price: float
    weekly_volume: float
    spread: float
    max_units: int
    profit_estimate: float
    roi: float

from typing import List, Dict, Any
from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session

app = FastAPI()

@app.get(
    "/top",
    response_model=List[ItemProfit],
    summary="Top N profitable items",
    description="Fetch the top N items sorted by profit estimate. Default is 10.",
)
def get_top(
    top: int = Query(
        10,
        title="Number of items",
        description="How many top items to return (10–100)",
        ge=10,
        le=100,
    ),
    db: Session = Depends(get_db),
) -> List[ItemProfit]:
    # 1) Latest snapshot per item
    subq = (
        db.query(
            Bazaar.product_id.label("item_id"),
            Bazaar.data['sellPrice'].as_float().label("sell_price"),
            Bazaar.data['buyPrice'].as_float().label("buy_price"),
            Bazaar.data['sellMovingWeek'].as_float().label("weekly_volume"),
        )
        .order_by(Bazaar.product_id, Bazaar.timestamp.desc())
        .distinct(Bazaar.product_id)
        .subquery()
    )

    rows = db.query(subq).all()

    scored: List[Dict[str, Any]] = []
    for item_id, sell_p, buy_p, vol_w in rows:
        # a) must have nonzero, sane prices & volume
        if not (sell_p and buy_p and vol_w and sell_p > 0 and buy_p > 0):
            continue

        # b) compute per-unit spread
        spread = buy_p - sell_p
        if spread <= 0:
            continue

        # c) realistic caps
        cap_by_money  = int(CAPITAL // buy_p)
        cap_by_market = int(MARKET_SHARE * vol_w)
        units_max     = min(cap_by_money, cap_by_market)
        if units_max < 1:
            continue

        # d) profit & ROI
        profit = (spread * units_max) / SCALING_FACTOR
        roi    = profit / CAPITAL

        scored.append({
            "item_id":         item_id,
            "sell_price":      sell_p,
            "buy_price":       buy_p,
            "weekly_volume":   vol_w,
            "spread":          spread,
            "max_units":       units_max,
            "profit_estimate": profit,
            "roi":             roi
        })

    # sort descending by profit
    scored.sort(key=lambda x: x["profit_estimate"], reverse=True)

    # return only the top N
    return scored[:top]


@app.get("/elections", summary="List mayoral elections")
def get_elections(
    range: str = Query('1week', description="all,6months,2months,1week,1day,latest"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    td = parse_range(range)
    start = None if range == 'all' or td is None else now - td
    q = db.query(Election.year, Election.mayor, Election.timestamp)
    q = apply_time_filters(q, Election.timestamp, start, now)
    rows = q.order_by(Election.timestamp).all()
    return [{"year": y, "mayor": m, "timestamp": t.isoformat()} for y,m,t in rows]


@app.get("/items", summary="Aggregate tracked item IDs")
def list_items(db: Session = Depends(get_db)) -> List[str]:
    baz_ids = db.query(Bazaar.product_id).distinct().all()
    return sorted({i[0] for i in baz_ids})