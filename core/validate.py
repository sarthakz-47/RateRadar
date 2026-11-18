"""Data-quality checks for the scraped competitor-rate feed."""
import pandas as pd

from .config import HORIZON_DAYS, MAX_STALE_HOURS

REQUIRED = ["hotel_id", "stay_date", "price", "scraped_at"]


def validate_rates(df: pd.DataFrame, horizon: int = HORIZON_DAYS, max_stale_hours: int = MAX_STALE_HOURS):
    """Return (clean_df, report). Never mutates the input."""
    report = {"rows_in": int(len(df)), "issues": []}
    if df.empty:
        report.update(rows_out=0, status="fail")
        report["issues"].append("feed is empty")
        return df, report

    df = df.copy()
    for col in REQUIRED:
        if col not in df.columns:
            df[col] = None
    if "available" not in df.columns:
        df["available"] = True
    if "hotel_name" not in df.columns:
        df["hotel_name"] = df["hotel_id"]

    df["stay_date"] = pd.to_datetime(df["stay_date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce", utc=True)
    df["available"] = df["available"].fillna(True).astype(bool)

    # 1. missing / non-positive values
    bad = df[REQUIRED].isna().any(axis=1) | (df["price"] <= 0)
    report["dropped_missing"] = int(bad.sum())
    df = df[~bad]

    # 2. duplicates (keep the most recent scrape)
    before = len(df)
    df = df.sort_values("scraped_at").drop_duplicates(["hotel_id", "stay_date"], keep="last")
    report["dropped_duplicates"] = int(before - len(df))

    # 3. price outliers vs each hotel's own median (e.g. 10x typos)
    if len(df):
        med = df.groupby("hotel_id")["price"].transform("median")
        out = (df["price"] > 3 * med) | (df["price"] < 0.3 * med)
        report["dropped_outliers"] = int(out.sum())
        df = df[~out]
    else:
        report["dropped_outliers"] = 0

    report["rows_out"] = int(len(df))
    if df.empty:
        report["status"] = "fail"
        report["issues"].append("no valid rows after cleaning")
        return df, report

    # 4. freshness
    age_h = (pd.Timestamp.now(tz="UTC") - df["scraped_at"].max()).total_seconds() / 3600
    report["feed_age_hours"] = round(age_h, 2)

    # 5. coverage: share of the horizon each hotel has a price for
    cov = df.groupby("hotel_id")["stay_date"].nunique() / (horizon + 1)
    report["hotels"] = int(len(cov))
    report["min_coverage"] = round(float(cov.min()), 2)

    status = "ok"
    if age_h > max_stale_hours:
        status = "fail"
        report["issues"].append(f"feed is stale ({age_h:.1f}h old)")
    if report["min_coverage"] < 0.9:
        status = "warn" if status == "ok" else status
        report["issues"].append(f"low coverage (min {report['min_coverage']:.0%})")
    if report["dropped_outliers"] > 0.05 * report["rows_in"]:
        status = "warn" if status == "ok" else status
        report["issues"].append("unusually many price outliers")
    report["status"] = status
    return df.reset_index(drop=True), report
