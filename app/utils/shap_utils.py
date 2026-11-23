"""SHAP explanations for the structured risk models.

Why this replaces the previous implementation
---------------------------------------------
The old code built the SHAP *background* from the single row being explained. With a
one-row background every feature already equals its "average", so every SHAP value is 0
(for the Logistic-Regression diabetes model and the SVM heart/liver models alike).

Here the background is a stratified sample of the real training data, and every model
(LR / SVM / tree / anything with predict_proba) is explained with KernelExplainer on the
*probability* output. Contributions are therefore in percentage points of risk and add up
exactly:  base_rate + sum(contributions) = predicted risk.
"""
import logging

import numpy as np
import pandas as pd
import shap

from app.utils.config import REFERENCE_DIR
from app.utils.predict import load_model

logging.getLogger("shap").setLevel(logging.ERROR)

_explainers = {}
N_BACKGROUND = 25          # k-means summary of the 150-row background
MAX_NSAMPLES = 1500        # exact enumeration is used automatically for <= 10 features


def _background(name):
    art = load_model(name)
    feats = art["features"]
    raw = pd.read_csv(REFERENCE_DIR / f"{name}_background.csv")[feats]
    imputed = pd.DataFrame(art["imputer"].transform(raw), columns=feats)
    return pd.DataFrame(art["scaler"].transform(imputed), columns=feats)


def _get_explainer(name):
    if name in _explainers:
        return _explainers[name]
    art = load_model(name)
    feats, model = art["features"], art["model"]
    bg = _background(name)

    def f(z):
        return model.predict_proba(pd.DataFrame(np.atleast_2d(z), columns=feats))[:, 1]

    explainer = shap.KernelExplainer(f, shap.kmeans(bg, N_BACKGROUND))
    _explainers[name] = (explainer, len(feats))
    return _explainers[name]


def explain(name, X_scaled: pd.DataFrame):
    """Returns (base_rate_pct, {feature: contribution_in_percentage_points})."""
    explainer, m = _get_explainer(name)
    nsamples = min(2 ** m - 2, MAX_NSAMPLES)
    sv = explainer.shap_values(X_scaled.iloc[[0]].values, nsamples=nsamples, silent=True, l1_reg=False)
    sv = np.asarray(sv[1] if isinstance(sv, list) else sv).reshape(-1)
    feats = list(X_scaled.columns)
    base = float(np.ravel(explainer.expected_value)[0]) * 100
    return base, {f: float(v) * 100 for f, v in zip(feats, sv)}
