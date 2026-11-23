"""Model loading and prediction (symptom classifier + the three structured risk models)."""
import json
import math
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from app.utils.config import (MODELS_DIR, REFERENCE_DIR, RISK_HIGH_FROM, RISK_MEDIUM_FROM)
from app.utils.schemas import SPECS, range_status

_cache = {}


# ---------------------------------------------------------------- loading
def load_model(name):
    """Load and cache all artifacts for a model. Fast after the first call."""
    if name in _cache:
        return _cache[name]
    if name == "symptom":
        art = {
            "model": joblib.load(MODELS_DIR / "symptom_model.pkl"),
            "le": joblib.load(MODELS_DIR / "symptom_label_encoder.pkl"),
            "features": joblib.load(MODELS_DIR / "symptom_features.pkl"),
            "name": joblib.load(MODELS_DIR / "symptom_model_name.pkl"),
        }
    else:
        art = {
            "model": joblib.load(MODELS_DIR / f"{name}_model.pkl"),
            "scaler": joblib.load(MODELS_DIR / f"{name}_scaler.pkl"),
            "imputer": joblib.load(MODELS_DIR / f"{name}_imputer.pkl"),
            "features": joblib.load(MODELS_DIR / f"{name}_features.pkl"),
            "name": joblib.load(MODELS_DIR / f"{name}_model_name.pkl"),
        }
    _cache[name] = art
    return art


@lru_cache(maxsize=None)
def load_reference(name):
    p = REFERENCE_DIR / f"{name}_reference.json"
    return json.loads(p.read_text()) if p.exists() else {"features": {}, "prevalence": None}


# ------------------------------------------------------- symptom classifier
NB_EPS = 0.02          # Laplace-style smoothing for the symptom-profile model
ENSEMBLE_W_XGB = 0.5   # weight of XGBoost in the final probability (rest = profile model)


def _symptom_vector(symptoms, features):
    s = set(symptoms)
    return np.array([[1 if f in s else 0 for f in features]])


@lru_cache(maxsize=1)
def _profile_matrix():
    """class x feature matrix of P(symptom | disease) learnt from the training data."""
    from app.utils.knowledge import _profile
    art = load_model("symptom")
    prof = _profile()
    return np.array([[prof.get(c, {}).get(f, 0.0) for f in art["features"]] for c in art["le"].classes_])


def _nb_proba(symptoms, negated=()):
    """Naive-Bayes posterior over diseases from the symptom profile (uniform prior).
    Symptoms the person explicitly denied count against diseases that usually have them."""
    art = load_model("symptom")
    F = _profile_matrix()
    have = _symptom_vector(symptoms, art["features"])[0]
    neg = _symptom_vector([n for n in negated if n not in set(symptoms)], art["features"])[0]
    ll = (have * np.log(F + NB_EPS)).sum(1) + (neg * np.log(1 - F + NB_EPS)).sum(1)
    p = np.exp(ll - ll.max())
    return p / p.sum()


def symptom_proba(symptoms, negated=()):
    """Returns (ensemble, xgboost, profile) probability vectors aligned with the label encoder.

    XGBoost alone is trained on *complete* symptom patterns and becomes erratic when a person
    reports only 3-5 symptoms. Averaging it with the symptom-profile model lifts top-1 accuracy on
    4-symptom inputs from ~80% to ~96% (see scripts/benchmark_symptom_ensemble.py)."""
    art = load_model("symptom")
    px = art["model"].predict_proba(_symptom_vector(symptoms, art["features"]))[0]
    pn = _nb_proba(symptoms, negated)
    return ENSEMBLE_W_XGB * px + (1 - ENSEMBLE_W_XGB) * pn, px, pn


def predict_symptom(symptom_list, k=3, negated=()):
    """Returns (top-k disease labels, top-k probabilities)."""
    art = load_model("symptom")
    proba, _, _ = symptom_proba(symptom_list, negated)
    idx = np.argsort(proba)[::-1][:k]
    return list(art["le"].inverse_transform(idx)), [float(p) for p in proba[idx]]


def symptom_impact(symptom_list, negated=()):
    """Leave-one-out impact of each symptom on the TOP disease's probability (percentage points).
    Positive = the symptom pushes the prediction towards the top disease."""
    base, _, _ = symptom_proba(symptom_list, negated)
    top = int(np.argmax(base))
    rows = []
    for s in symptom_list:
        reduced = [x for x in symptom_list if x != s]
        p = symptom_proba(reduced, negated)[0][top] if reduced else 0.0
        rows.append((s, float((base[top] - p) * 100)))
    rows.sort(key=lambda r: abs(r[1]), reverse=True)
    return rows


def confidence_band(prob):
    return "HIGH" if prob > 0.6 else "MEDIUM" if prob > 0.3 else "LOW"


# ---------------------------------------------------- structured risk models
def risk_level(risk_pct):
    if risk_pct < RISK_MEDIUM_FROM:
        return "LOW"
    if risk_pct < RISK_HIGH_FROM:
        return "MEDIUM"
    return "HIGH"


def prepare(name, input_dict):
    """Model-ready (imputed + scaled) one-row DataFrame. Missing values -> NaN -> imputed."""
    art = load_model(name)
    feats = art["features"]
    row = [np.nan if input_dict.get(f) is None else input_dict.get(f) for f in feats]
    df = pd.DataFrame([row], columns=feats, dtype=float)
    imp = pd.DataFrame(art["imputer"].transform(df), columns=feats)
    return pd.DataFrame(art["scaler"].transform(imp), columns=feats)


def predict_disease(name, input_dict):
    """Returns (risk_pct, level, X_scaled)."""
    art = load_model(name)
    X = prepare(name, input_dict)
    risk = float(art["model"].predict_proba(X)[0][1] * 100)
    return risk, risk_level(risk), X


def predict_risk_only(name, ui_values):
    """Fast path used by the what-if simulator."""
    spec = SPECS[name]
    risk, level, _ = predict_disease(name, spec.encode(ui_values))
    return risk, level


def _percentile(sorted_sample, v):
    if not sorted_sample:
        return None
    arr = np.asarray(sorted_sample)
    return float((arr <= v).mean() * 100)


def run_assessment(name, ui_values):
    """Full, JSON-serialisable assessment: risk, SHAP factors, reference comparison, warnings."""
    from app.utils.shap_utils import explain  # local import: shap is heavy

    spec = SPECS[name]
    art = load_model(name)
    model_input = spec.encode(ui_values)
    risk, level, X = predict_disease(name, model_input)
    base, contribs = explain(name, X)
    ref = load_reference(name)["features"]

    factors, comparison, warnings, unknown = [], [], [], []
    for f in spec.fields:
        val = ui_values.get(f.key)
        pts = float(sum(contribs.get(m, 0.0) for m in f.model_features))
        is_unknown = f.optional and val is None
        if is_unknown:
            unknown.append(f.label)
        factors.append({
            "key": f.key, "label": f.label,
            "value": None if val is None else (val if isinstance(val, (int, float, str)) else str(val)),
            "display": "Not provided (typical value assumed)" if is_unknown else f.label_for(val),
            "contribution": pts,
        })
        if f.kind == "number":
            stats = ref.get(f.key, {})
            row = {"key": f.key, "label": f.label, "unit": f.unit, "value": val, "ref_text": f.ref_text,
                   "status": range_status(f, val), "median_neg": stats.get("median_neg"),
                   "median_pos": stats.get("median_pos"),
                   "percentile": _percentile(stats.get("sorted_sample"), val) if val is not None else None}
            comparison.append(row)
            if val is not None and stats and (val < stats["min"] or val > stats["max"]):
                warnings.append(f"{f.label} ({f.label_for(val)}) is outside the range the model was trained on "
                                f"({stats['min']:g} – {stats['max']:g}); the estimate may be less reliable.")
    factors.sort(key=lambda r: abs(r["contribution"]), reverse=True)
    gap = abs((base + sum(c for c in contribs.values())) - risk)

    return {
        "disease": name, "title": spec.short, "risk_pct": risk, "level": level,
        "model_name": str(art["name"]), "base_pct": float(base), "ui_values": _jsonable(ui_values),
        "model_input": _jsonable(model_input), "factors": factors, "comparison": _jsonable(comparison),
        "warnings": warnings, "unknown": unknown, "additivity_gap": float(gap),
    }


def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) and math.isnan(o)) else float(o)
    return o
