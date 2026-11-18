from datetime import date

from core.events import load_events
from core.features import FEATURES, build_features
from core.model import occupancy_to_label, train_models
from core.simulate import generate_history


def test_labels():
    assert occupancy_to_label(30) == "low"
    assert occupancy_to_label(60) == "medium"
    assert occupancy_to_label(90) == "high"


def test_model_learns_something():
    events = load_events()
    hist = generate_history(end=date(2026, 11, 1), days=730, events=events)
    X = build_features(hist["stay_date"], hist["comp_avg_price"], events)
    y = hist["occupancy"].map(occupancy_to_label).to_numpy()
    assert list(X.columns) == FEATURES
    model, best, results = train_models(X, y)
    assert best in ("decision_tree", "svm")
    assert results[best]["accuracy"] > 0.6   # well above the ~0.33 of random guessing
    assert set(model.predict(X.head(10))) <= {"low", "medium", "high"}
