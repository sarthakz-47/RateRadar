import pandas as pd

from core.validate import validate_rates


def _rows(n=61, price=4000, hotel="h1", scraped=None):
    scraped = scraped or pd.Timestamp.now(tz="UTC").isoformat()
    days = pd.date_range("2026-01-01", periods=n)
    return pd.DataFrame({"hotel_id": hotel, "hotel_name": hotel, "stay_date": days.astype(str),
                         "price": price, "available": True, "scraped_at": scraped})


def test_clean_feed_is_ok():
    clean, rep = validate_rates(_rows())
    assert rep["status"] == "ok" and len(clean) == 61


def test_drops_missing_and_outliers_and_duplicates():
    df = _rows()
    df.loc[0, "price"] = None
    df.loc[1, "price"] = 40000          # 10x typo
    df = pd.concat([df, df.iloc[[5]]])  # duplicate
    clean, rep = validate_rates(df)
    assert rep["dropped_missing"] == 1
    assert rep["dropped_outliers"] == 1
    assert rep["dropped_duplicates"] == 1
    assert len(clean) == 61 - 2


def test_stale_feed_fails():
    old = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=48)).isoformat()
    _, rep = validate_rates(_rows(scraped=old))
    assert rep["status"] == "fail"


def test_low_coverage_warns():
    _, rep = validate_rates(_rows(n=20))
    assert rep["status"] == "warn"


def test_empty_feed_fails():
    _, rep = validate_rates(pd.DataFrame())
    assert rep["status"] == "fail"
