"""
Benchmark: XGBoost vs symptom-profile Naive Bayes vs the ensemble used in the app,
when only k of a patient's symptoms are reported (what real users do).

Run from the project root:   python scripts/benchmark_symptom_ensemble.py
Writes reports/symptom_ensemble_benchmark.csv

NOTE: the dataset is synthetic and both models were fitted on it, so these numbers are in-sample;
use them to compare the methods against each other, not as real-world accuracy.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.predict import ENSEMBLE_W_XGB, NB_EPS, _profile_matrix, load_model  # noqa: E402

art = load_model("symptom")
feats, classes = art["features"], list(art["le"].classes_)
data = pd.read_csv(ROOT / "data" / "processed" / "symptoms_binary.csv")
X, y = data[feats].values, np.array([classes.index(v) for v in data["Disease"]])
F = _profile_matrix()
rng = np.random.default_rng(0)


def nb(x):
    ll = (x[:, None, :] * np.log(F[None] + NB_EPS)).sum(2)
    p = np.exp(ll - ll.max(1, keepdims=True))
    return p / p.sum(1, keepdims=True)


def topn(p, n):
    return float(np.mean([y[i] in np.argsort(p[i])[::-1][:n] for i in range(len(y))]))


rows = []
for k in (2, 3, 4, 5, 6, 8, 10):
    sub = np.zeros_like(X)
    for i in range(len(X)):
        on = np.flatnonzero(X[i])
        sub[i, rng.choice(on, size=min(k, len(on)), replace=False)] = 1
    px, pn = art["model"].predict_proba(sub), nb(sub)
    pe = ENSEMBLE_W_XGB * px + (1 - ENSEMBLE_W_XGB) * pn
    for name, p in (("XGBoost", px), ("Profile (Naive Bayes)", pn), ("Ensemble (used in app)", pe)):
        rows.append({"Symptoms reported": k, "Model": name, "Top-1 accuracy": round(topn(p, 1), 3), "Top-3 accuracy": round(topn(p, 3), 3)})
out = pd.DataFrame(rows)
out.to_csv(ROOT / "reports" / "symptom_ensemble_benchmark.csv", index=False)
print(out.pivot(index="Symptoms reported", columns="Model", values="Top-1 accuracy"))
