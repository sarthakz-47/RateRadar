"""Synthetic data used by the mock OTA and the history seeder.

In production this would be replaced by real OTA rates and the hotel's PMS data.
"""
import random
import zlib

import numpy as np
import pandas as pd

from .config import BASE_RATE
from .events import event_impact, load_events

HOTELS = [
    {"id": "h1", "name": "Seaview Residency", "base": 4200},
    {"id": "h2", "name": "Marine Drive Suites", "base": 5200},
    {"id": "h3", "name": "Juhu Palm Inn", "base": 3600},
    {"id": "h4", "name": "Bandra Boutique Stay", "base": 4800},
    {"id": "h5", "name": "Airport Comfort Hotel", "base": 3300},
    {"id": "h6", "name": "Colaba Heritage", "base": 5600},
]


def _season(month: int) -> float:
    if month in (10, 11, 12, 1, 2):
        return 1.10
    if month in (6, 7, 8):
        return 0.90
    return 1.0


def competitor_price(base: int, d, impact: int) -> int:
    rng = random.Random(zlib.crc32(f"{base}-{d.isoformat()}".encode()))
    price = base * _season(d.month) * (1 + 0.12 * impact)
    if d.weekday() in (4, 5):
        price *= 1.18
    price *= rng.uniform(0.95, 1.05)
    return int(round(price / 10) * 10)


def is_sold_out(base: int, d, impact: int) -> bool:
    rng = random.Random(zlib.crc32(f"sold-{base}-{d.isoformat()}".encode()))
    return rng.random() < 0.03 + 0.05 * impact


def generate_history(end, days: int = 730, seed: int = 7, events=None) -> pd.DataFrame:
    """Fake 'our hotel' history: occupancy + competitor average per date."""
    events = load_events() if events is None else events
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=end, periods=days)
    impact = event_impact(dates, events)
    comp = [
        float(np.mean([competitor_price(h["base"], d.date(), int(i)) for h in HOTELS]))
        for d, i in zip(dates, impact)
    ]
    season = np.where(
        np.isin(dates.month, [10, 11, 12, 1, 2]), 8, np.where(np.isin(dates.month, [6, 7, 8]), -8, 0)
    )
    weekend = np.isin(dates.dayofweek, [4, 5]).astype(int)
    occ = 52 + 14 * weekend + 10 * impact + season + rng.normal(0, 6, days)
    occ = np.clip(occ, 15, 100)
    return pd.DataFrame(
        {
            "stay_date": [d.date() for d in dates],
            "occupancy": occ.round(1),
            "adr": (BASE_RATE * (0.8 + occ / 250)).round(0),
            "comp_avg_price": np.round(comp, 0),
        }
    )
