"""
Build the small, git-friendly runtime assets the app needs.

Why: the app should not depend on the big (git-ignored) CSVs in data/ at runtime.
This script produces, under app/assets/:
  reference/<disease>_background.csv   150-row raw sample used as the SHAP background
  reference/<disease>_reference.json   per-feature percentiles + class medians
  knowledge/disease_symptom_profile.json   how often each symptom occurs per disease
  knowledge/*.csv                      descriptions / precautions / severity weights

Run from the project root:   python scripts/build_assets.py
"""
import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT_REF = ROOT / "app" / "assets" / "reference"
OUT_KNOW = ROOT / "app" / "assets" / "knowledge"
OUT_REF.mkdir(parents=True, exist_ok=True)
OUT_KNOW.mkdir(parents=True, exist_ok=True)

TARGETS = {"diabetes": "Outcome", "heart": "HeartDisease", "liver": "Dataset"}


def build_reference(name: str, target: str) -> None:
    df = pd.read_csv(PROC / f"{name}_clean.csv")
    feats = [c for c in df.columns if c != target]
    X = df[feats]

    # Stratified 150-row background sample (raw units, NaNs preserved: the imputer handles them)
    per_class = 75
    parts = [g.sample(min(per_class, len(g)), random_state=42) for _, g in df.groupby(target)]
    bg = pd.concat(parts)[feats].reset_index(drop=True)
    bg.to_csv(OUT_REF / f"{name}_background.csv", index=False)

    ref = {"n_rows": int(len(df)), "prevalence": float(df[target].mean()), "features": {}}
    for f in feats:
        s = X[f].dropna()
        pos, neg = df.loc[df[target] == 1, f].dropna(), df.loc[df[target] == 0, f].dropna()
        ref["features"][f] = {
            "min": float(s.min()), "max": float(s.max()),
            "p5": float(s.quantile(0.05)), "p25": float(s.quantile(0.25)),
            "median": float(s.median()),
            "p75": float(s.quantile(0.75)), "p95": float(s.quantile(0.95)),
            "median_pos": float(pos.median()), "median_neg": float(neg.median()),
            "sorted_sample": [round(float(v), 4) for v in s.sort_values().iloc[:: max(1, len(s) // 200)]],
        }
    (OUT_REF / f"{name}_reference.json").write_text(json.dumps(ref))
    print(f"  {name}: background {bg.shape}, reference for {len(feats)} features")


def build_symptom_profile() -> None:
    b = pd.read_csv(PROC / "symptoms_binary.csv")
    sym_cols = [c for c in b.columns if c != "Disease"]
    profile = {}
    for disease, g in b.groupby("Disease"):
        freq = g[sym_cols].mean()
        profile[str(disease)] = {s: round(float(v), 3) for s, v in freq.items() if v > 0}
    (OUT_KNOW / "disease_symptom_profile.json").write_text(json.dumps(profile))
    print(f"  symptom profile: {len(profile)} diseases")


if __name__ == "__main__":
    print("Building runtime assets...")
    for n, t in TARGETS.items():
        build_reference(n, t)
    build_symptom_profile()
    for f in ["Symptom-severity.csv", "symptom_Description.csv", "symptom_precaution.csv"]:
        shutil.copy(RAW / f, OUT_KNOW / f)
    print("Done ->", ROOT / "app" / "assets")
