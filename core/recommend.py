from datetime import timedelta

import pandas as pd

from .config import BASE_RATE, MAX_RATE, MIN_RATE
from .features import build_features

DEMAND_MULTIPLIER = {"low": 0.90, "medium": 1.00, "high": 1.15}
MAX_PREMIUM = 1.15   # never go more than 15% above competitor average
MAX_DISCOUNT = 0.85  # never go more than 15% below it (unless demand is low)


def recommend_rate(demand, comp_avg, base=BASE_RATE, min_rate=MIN_RATE, max_rate=MAX_RATE):
    mult = DEMAND_MULTIPLIER[demand]
    rate = base * mult
    notes = [f"Demand predicted {demand}: base Rs {base:,.0f} x {mult}"]

    if rate > comp_avg * MAX_PREMIUM:
        rate = comp_avg * MAX_PREMIUM
        notes.append(f"capped to 15% above competitor avg (Rs {comp_avg:,.0f})")
    elif rate < comp_avg * MAX_DISCOUNT and demand != "low":
        rate = comp_avg * MAX_DISCOUNT
        notes.append(f"raised to 15% below competitor avg (Rs {comp_avg:,.0f})")
    else:
        notes.append(f"competitor avg is Rs {comp_avg:,.0f}")

    clamped = min(max(rate, min_rate), max_rate)
    if clamped != rate:
        notes.append(f"clamped to guardrail Rs {clamped:,.0f}")
    final = int(round(clamped / 50) * 50)
    return final, "; ".join(notes)


def generate_recommendations(model, rates: pd.DataFrame, events: pd.DataFrame, start, days: int = 30):
    """Returns (recommendations, skipped_dates). Dates with no competitor data are skipped."""
    if rates.empty:
        return [], [start + timedelta(d) for d in range(days)]

    comp = rates[rates["available"]].groupby("stay_date")["price"].mean()
    dates = [start + timedelta(d) for d in range(days)]
    usable = [d for d in dates if d in comp.index]
    skipped = [d for d in dates if d not in comp.index]
    if not usable:
        return [], skipped

    X = build_features(usable, [comp[d] for d in usable], events)
    labels = model.predict(X)
    recs = []
    for d, label, avg in zip(usable, labels, X["comp_avg_price"]):
        rate, reason = recommend_rate(label, float(avg))
        recs.append(
            {"stay_date": d, "demand": label, "comp_avg": round(float(avg), 0),
             "recommended_rate": rate, "reason": reason}
        )
    return recs, skipped
