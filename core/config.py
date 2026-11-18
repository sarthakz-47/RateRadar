import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/rateradar")
PMS_URL = os.getenv("PMS_URL", "http://localhost:5001/pms/rates")
PMS_API_KEY = os.getenv("PMS_API_KEY", "dev-key")

# "Our" hotel pricing guardrails (INR)
BASE_RATE = float(os.getenv("BASE_RATE", 4000))
MIN_RATE = float(os.getenv("MIN_RATE", 2800))
MAX_RATE = float(os.getenv("MAX_RATE", 8000))

HORIZON_DAYS = 60          # how far ahead we rate-shop
MAX_STALE_HOURS = 24       # feed older than this = unhealthy

RAW_FEED = ROOT / "data" / "raw" / "latest.jsonl"
EVENTS_CSV = ROOT / "data" / "events.csv"
MODEL_PATH = ROOT / "models" / "demand_model.joblib"
