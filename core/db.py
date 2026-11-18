from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy import (Boolean, Column, Date, DateTime, Float, Integer, MetaData, String,
                        Table, Text, create_engine, delete, select, text, update)

from .config import DATABASE_URL

metadata = MetaData()

competitor_rates = Table(
    "competitor_rates", metadata,
    Column("hotel_id", String(20), primary_key=True),
    Column("stay_date", Date, primary_key=True),
    Column("hotel_name", String(100)),
    Column("price", Integer, nullable=False),
    Column("available", Boolean, default=True),
    Column("scraped_at", DateTime, nullable=False),
)

our_history = Table(
    "our_history", metadata,
    Column("stay_date", Date, primary_key=True),
    Column("occupancy", Float),
    Column("adr", Float),
    Column("comp_avg_price", Float),
)

recommendations = Table(
    "recommendations", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("stay_date", Date, nullable=False),
    Column("demand", String(10)),
    Column("comp_avg", Float),
    Column("recommended_rate", Integer),
    Column("reason", Text),
    Column("status", String(15), default="pending"),  # pending/approved/rejected/push_failed
    Column("created_at", DateTime),
)


def get_engine(url: str = None):
    return create_engine(url or DATABASE_URL, pool_pre_ping=True)


def init_db(engine):
    metadata.create_all(engine)


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- competitor rates ----------
def save_rates(engine, df: pd.DataFrame, today: date = None):
    """Replace the forward-looking snapshot (stay_date >= today) in one transaction."""
    today = today or date.today()
    recs = [
        {
            "hotel_id": r.hotel_id,
            "hotel_name": r.hotel_name,
            "stay_date": r.stay_date.date(),
            "price": int(r.price),
            "available": bool(r.available),
            "scraped_at": r.scraped_at.tz_convert("UTC").tz_localize(None).to_pydatetime(),
        }
        for r in df.itertuples()
    ]
    with engine.begin() as conn:
        conn.execute(delete(competitor_rates).where(competitor_rates.c.stay_date >= today))
        if recs:
            conn.execute(competitor_rates.insert(), recs)
    return len(recs)


def load_rates(engine, start: date = None, end: date = None) -> pd.DataFrame:
    q = select(competitor_rates)
    if start:
        q = q.where(competitor_rates.c.stay_date >= start)
    if end:
        q = q.where(competitor_rates.c.stay_date <= end)
    with engine.connect() as conn:
        df = pd.read_sql(q, conn)
    if not df.empty:
        df["stay_date"] = pd.to_datetime(df["stay_date"]).dt.date
        df["available"] = df["available"].astype(bool)
    return df


# ---------- history ----------
def save_history(engine, df: pd.DataFrame):
    with engine.begin() as conn:
        conn.execute(delete(our_history))
        conn.execute(our_history.insert(), df.to_dict("records"))


def load_history(engine) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(select(our_history).order_by(our_history.c.stay_date), conn)
    df["stay_date"] = pd.to_datetime(df["stay_date"]).dt.date
    return df


# ---------- recommendations ----------
def save_recommendations(engine, recs: list):
    if not recs:
        return 0
    now = _utcnow()
    rows = [{**r, "status": "pending", "created_at": now} for r in recs]
    dates = [r["stay_date"] for r in recs]
    with engine.begin() as conn:
        conn.execute(delete(recommendations).where(
            recommendations.c.status == "pending", recommendations.c.stay_date.in_(dates)))
        conn.execute(recommendations.insert(), rows)
    return len(rows)


def list_recommendations(engine, status: str = None) -> list:
    q = select(recommendations).order_by(recommendations.c.stay_date)
    if status:
        q = q.where(recommendations.c.status == status)
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(q)]


def get_recommendation(engine, rec_id: int):
    with engine.connect() as conn:
        row = conn.execute(select(recommendations).where(recommendations.c.id == rec_id)).first()
    return dict(row._mapping) if row else None


def set_status(engine, rec_id: int, status: str):
    with engine.begin() as conn:
        conn.execute(update(recommendations).where(recommendations.c.id == rec_id).values(status=status))


def ping(engine) -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
