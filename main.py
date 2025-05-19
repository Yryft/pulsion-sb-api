from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from db.session import SessionLocal
from db.models import Bazaar, Election

# Adjust this factor to scale volume impact in your profitability formula
SCALING_FACTOR = 1  # e.g., 1 (pure revenue), or larger to normalize large volumes

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


@app.get("/top", summary="Top 10 profitable items")
def get_top(db: Session = Depends(get_db)):
    # fetch all distinct items' latest data
    subq = (
        db.query(
            Bazaar.product_id,
            Bazaar.data['sellPrice'].as_float().label('sellPrice'),
            Bazaar.data['buyPrice'].as_float().label('buyPrice'),
            Bazaar.data['sellMovingWeek'].as_float().label('sellMovingWeek')
        )
        .order_by(Bazaar.product_id, Bazaar.timestamp.desc())
        .distinct(Bazaar.product_id)
        .subquery()
    )
    items = db.query(subq).all()

    # compute revenue estimate
    scored = []
    for pid, sell, buy, vol in items:
        if sell and buy is not None and vol and vol > 0:
            rev = (sell - buy) * vol / SCALING_FACTOR
            scored.append((pid, sell, buy, vol, rev))
    # sort and take top 10
    top10 = sorted(scored, key=lambda x: x[4], reverse=True)[:10]

    return [
        {
            "item_id": pid,
            "sell_price": sell,
            "buy_price": buy,
            "sell_moving_week": vol,
            "revenue_estimate": rev
        }
        for pid, sell, buy, vol, rev in top10
    ]


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