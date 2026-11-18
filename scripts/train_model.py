"""Train decision tree vs SVM on history and save the better one."""
from core.db import get_engine, load_history
from core.events import load_events
from core.features import build_features
from core.model import occupancy_to_label, save_model, train_models


def main():
    hist = load_history(get_engine()).sort_values("stay_date")
    X = build_features(hist["stay_date"], hist["comp_avg_price"], load_events())
    y = hist["occupancy"].map(occupancy_to_label).to_numpy()
    model, best, results = train_models(X, y)
    save_model(model, best)
    for name, m in results.items():
        print(f"{name:14s} accuracy={m['accuracy']}  f1_macro={m['f1_macro']}")
    print(f"Saved best model: {best}")


if __name__ == "__main__":
    main()
