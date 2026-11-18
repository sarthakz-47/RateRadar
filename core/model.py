import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from .config import MODEL_PATH


def occupancy_to_label(occ: float) -> str:
    return "low" if occ < 50 else "medium" if occ < 75 else "high"


def train_models(X: pd.DataFrame, y, test_frac: float = 0.2):
    """Compare a decision tree and an SVM on a chronological hold-out.

    X must already be sorted by date. Returns (final_model, best_name, results).
    """
    split = int(len(X) * (1 - test_frac))
    X_tr, X_te, y_tr, y_te = X.iloc[:split], X.iloc[split:], y[:split], y[split:]

    candidates = {
        "decision_tree": DecisionTreeClassifier(max_depth=5, min_samples_leaf=10, random_state=42),
        "svm": make_pipeline(StandardScaler(), SVC(kernel="rbf", C=1.0)),
    }
    results = {}
    for name, model in candidates.items():
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)
        results[name] = {
            "accuracy": round(float(accuracy_score(y_te, pred)), 3),
            "f1_macro": round(float(f1_score(y_te, pred, average="macro")), 3),
        }
    best = max(results, key=lambda n: results[n]["f1_macro"])
    final = clone(candidates[best]).fit(X, y)  # refit on all data
    return final, best, results


def save_model(model, name, path=MODEL_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "name": name}, path)


def load_model(path=MODEL_PATH):
    if not path.exists():
        raise FileNotFoundError("Model not trained yet. Run: python -m scripts.train_model")
    return joblib.load(path)["model"]
