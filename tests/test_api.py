"""API tests run against in-memory SQLite, so MySQL is not needed."""
from datetime import date, timedelta

import pandas as pd
import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from api import app as api_module
from core import db
from core.model import save_model, train_models
from core.features import build_features
from core.events import load_events
from core.model import occupancy_to_label
from core.simulate import generate_history


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    db.init_db(engine)
    api_module.app.config["ENGINE"] = engine

    # train a small model into a temp path
    events = load_events()
    hist = generate_history(end=date.today() - timedelta(days=1), days=400, events=events)
    X = build_features(hist["stay_date"], hist["comp_avg_price"], events)
    model, name, _ = train_models(X, hist["occupancy"].map(occupancy_to_label).to_numpy())
    path = tmp_path / "m.joblib"
    save_model(model, name, path)
    monkeypatch.setattr(api_module, "load_model", lambda: __import__("joblib").load(path)["model"])

    # load 20 days of competitor rates
    now = pd.Timestamp.now(tz="UTC")
    rows = [{"hotel_id": f"h{h}", "hotel_name": f"H{h}", "stay_date": pd.Timestamp(date.today() + timedelta(d)),
             "price": 4000 + 100 * h, "available": True, "scraped_at": now}
            for h in range(3) for d in range(20)]
    db.save_rates(engine, pd.DataFrame(rows))
    return api_module.app.test_client()


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["hotels"] == 3


def test_generate_then_approve_pushes_to_pms(client, monkeypatch):
    r = client.post("/recommendations/generate", json={"days": 10})
    assert r.get_json()["created"] == 10
    recs = client.get("/recommendations?status=pending").get_json()
    assert len(recs) == 10
    pushed = []
    monkeypatch.setattr(api_module, "push_rate", lambda d, rate: pushed.append((d, rate)))
    rid = recs[0]["id"]
    assert client.post(f"/recommendations/{rid}/approve").status_code == 200
    assert len(pushed) == 1
    assert client.post(f"/recommendations/{rid}/approve").status_code == 409  # already approved


def test_failed_push_is_recorded(client, monkeypatch):
    client.post("/recommendations/generate", json={"days": 3})
    rid = client.get("/recommendations").get_json()[0]["id"]

    def boom(*a):
        raise requests.ConnectionError()
    monkeypatch.setattr(api_module, "push_rate", boom)
    assert client.post(f"/recommendations/{rid}/approve").status_code == 502
    assert client.get("/recommendations?status=push_failed").get_json()[0]["id"] == rid


def test_reject(client):
    client.post("/recommendations/generate", json={"days": 2})
    rid = client.get("/recommendations").get_json()[0]["id"]
    assert client.post(f"/recommendations/{rid}/reject").status_code == 200
    assert client.post(f"/recommendations/{rid}/reject").status_code == 409
