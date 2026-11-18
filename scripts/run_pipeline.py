"""Load the crawler output, validate it, and store it in MySQL."""
import json
import sys

import pandas as pd

from core.config import RAW_FEED
from core.db import get_engine, init_db, save_rates
from core.validate import validate_rates


def main(feed=RAW_FEED):
    if not feed.exists() or feed.stat().st_size == 0:
        sys.exit(f"No feed at {feed}. Run the crawler first (see README).")
    df = pd.read_json(feed, lines=True, convert_dates=False)
    clean, report = validate_rates(df)
    print(json.dumps(report, indent=2))
    if report["status"] == "fail":
        sys.exit("Validation failed - nothing was written to the database.")
    engine = get_engine()
    init_db(engine)
    n = save_rates(engine, clean)
    print(f"Saved {n} rate rows.")


if __name__ == "__main__":
    main()
