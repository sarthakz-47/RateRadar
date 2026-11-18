import requests

from .config import PMS_API_KEY, PMS_URL


def push_rate(stay_date, rate: int) -> dict:
    """Push an approved rate to the (mock) PMS. Raises on failure."""
    resp = requests.post(
        PMS_URL,
        json={"stay_date": str(stay_date), "rate": int(rate)},
        headers={"X-API-Key": PMS_API_KEY},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
