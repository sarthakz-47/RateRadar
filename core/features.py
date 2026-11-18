import numpy as np
import pandas as pd

from .events import event_impact

FEATURES = ["dow", "is_weekend", "month", "event_impact", "comp_avg_price"]


def build_features(dates, comp_avg, events: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(pd.Series(list(dates))).reset_index(drop=True)
    return pd.DataFrame(
        {
            "dow": d.dt.dayofweek.to_numpy(),
            "is_weekend": d.dt.dayofweek.isin([4, 5]).astype(int).to_numpy(),  # Fri/Sat
            "month": d.dt.month.to_numpy(),
            "event_impact": event_impact(d, events),
            "comp_avg_price": np.asarray(list(comp_avg), dtype=float),
        }
    )[FEATURES]
