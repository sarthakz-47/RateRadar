"""RateRadar API.   Run: python -m api.app   (port 5000)"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from flask import Flask, jsonify, request, send_from_directory

from core import db
from core.config import HORIZON_DAYS, MAX_STALE_HOURS
from core.events import load_events
from core.model import load_model
from core.pms import push_rate
from core.recommend import generate_recommendations

app = Flask(__name__)
STATIC_DIR = Path(__file__).parent / "static"


def engine():
    if "ENGINE" not in app.config:
        app.config["ENGINE"] = db.get_engine()
    return app.config["ENGINE"]


def _jsonable(rec: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in rec.items()}


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/health")
def health():
    try:
        db.ping(engine())
    except Exception as exc:  # DB down
        return jsonify(status="fail", issue=f"database unreachable: {exc.__class__.__name__}"), 503
    rates = db.load_rates(engine(), start=date.today())
    if rates.empty:
        return jsonify(status="fail", issue="no competitor rates loaded"), 503
    last = pd.Timestamp(rates["scraped_at"].max()).tz_localize("UTC")
    age_h = (pd.Timestamp.now(tz="UTC") - last).total_seconds() / 3600
    ok = age_h <= MAX_STALE_HOURS
    return jsonify(
        status="ok" if ok else "stale",
        last_scrape=last.isoformat(),
        feed_age_hours=round(age_h, 2),
        hotels=int(rates["hotel_id"].nunique()),
        days_covered=int(rates["stay_date"].nunique()),
    ), (200 if ok else 503)


@app.get("/rates")
def rates():
    try:
        start = date.fromisoformat(request.args.get("from", date.today().isoformat()))
        end = date.fromisoformat(request.args.get("to", (start + timedelta(days=13)).isoformat()))
    except ValueError:
        return jsonify(error="from/to must be YYYY-MM-DD"), 400
    df = db.load_rates(engine(), start, end)
    if df.empty:
        return jsonify([])
    avail = df[df["available"]]
    g = avail.groupby("stay_date")["price"].agg(avg="mean", min="min", max="max", hotels="count").round(0)
    out = [{"stay_date": d.isoformat(), **{k: int(v) for k, v in row.items()}} for d, row in g.iterrows()]
    return jsonify(out)


@app.post("/recommendations/generate")
def generate():
    body = request.get_json(silent=True) or {}
    days = min(max(int(body.get("days", 30)), 1), HORIZON_DAYS)
    try:
        model = load_model()
    except FileNotFoundError as exc:
        return jsonify(error=str(exc)), 409
    start = date.today()
    df = db.load_rates(engine(), start, start + timedelta(days=days))
    recs, skipped = generate_recommendations(model, df, load_events(), start, days)
    saved = db.save_recommendations(engine(), recs)
    return jsonify(created=saved, skipped_dates_no_data=[d.isoformat() for d in skipped])


@app.get("/recommendations")
def list_recs():
    recs = db.list_recommendations(engine(), request.args.get("status"))
    return jsonify([_jsonable(r) for r in recs])


@app.post("/recommendations/<int:rec_id>/approve")
def approve(rec_id):
    rec = db.get_recommendation(engine(), rec_id)
    if not rec:
        return jsonify(error="not found"), 404
    if rec["status"] not in ("pending", "push_failed"):
        return jsonify(error=f"already {rec['status']}"), 409
    try:
        push_rate(rec["stay_date"], rec["recommended_rate"])
    except requests.RequestException as exc:
        db.set_status(engine(), rec_id, "push_failed")
        return jsonify(error=f"PMS push failed: {exc.__class__.__name__}"), 502
    db.set_status(engine(), rec_id, "approved")
    return jsonify(status="approved", pushed_to_pms=True)


@app.post("/recommendations/<int:rec_id>/reject")
def reject(rec_id):
    rec = db.get_recommendation(engine(), rec_id)
    if not rec:
        return jsonify(error="not found"), 404
    if rec["status"] != "pending":
        return jsonify(error=f"already {rec['status']}"), 409
    db.set_status(engine(), rec_id, "rejected")
    return jsonify(status="rejected")


if __name__ == "__main__":
    app.run(port=5000, debug=True)
