"""Create tables and load 2 years of synthetic 'our hotel' history."""
from datetime import date, timedelta

from core.db import get_engine, init_db, save_history
from core.simulate import generate_history


def main():
    engine = get_engine()
    init_db(engine)
    df = generate_history(end=date.today() - timedelta(days=1))
    save_history(engine, df)
    print(f"Seeded {len(df)} days of history.")


if __name__ == "__main__":
    main()
