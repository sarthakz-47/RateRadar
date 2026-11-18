import numpy as np
import pandas as pd

from .config import EVENTS_CSV


def load_events(path=EVENTS_CSV) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["start", "end"])


def event_impact(dates, events: pd.DataFrame) -> np.ndarray:
    """Highest event impact (0-3) falling on each date."""
    d = pd.to_datetime(pd.Series(list(dates))).reset_index(drop=True)
    impact = np.zeros(len(d), dtype=int)
    for _, ev in events.iterrows():
        mask = ((d >= ev["start"]) & (d <= ev["end"])).to_numpy()
        impact[mask] = np.maximum(impact[mask], int(ev["impact"]))
    return impact
