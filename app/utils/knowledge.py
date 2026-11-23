"""Medical knowledge helpers for the symptom checker: descriptions, precautions,
severity scoring, red-flag detection and smart follow-up questions."""
import json
import re
from functools import lru_cache

import pandas as pd

from app.utils.config import KNOWLEDGE_DIR

# Dataset labels contain typos / stray spaces -> clean display names
_FIX = {
    "(vertigo) paroymsal positional vertigo": "Paroxysmal Positional Vertigo",
    "peptic ulcer diseae": "Peptic Ulcer Disease",
    "osteoarthristis": "Osteoarthritis",
    "dimorphic hemmorhoids(piles)": "Hemorrhoids (Piles)",
    "hepatitis a": "Hepatitis A",
    "gerd": "GERD",
    "aids": "AIDS",
    "diabetes": "Diabetes",
    "hypertension": "Hypertension",
    "paralysis (brain hemorrhage)": "Paralysis (Brain Hemorrhage)",
}


def _key(label: str) -> str:
    return re.sub(r"\s+", " ", str(label).strip().lower())


def clean_disease_name(label: str) -> str:
    k = _key(label)
    return _FIX.get(k, re.sub(r"\s+", " ", str(label).strip()).title() if k.islower() else re.sub(r"\s+", " ", str(label).strip()))


def pretty_symptom(sym: str) -> str:
    s = re.sub(r"[_()]", " ", sym)
    s = re.sub(r"\s+", " ", s).strip()
    fixes = {"cold hands and feets": "cold hands and feet", "dischromic patches": "discoloured patches",
             "scurring": "skin scarring", "swollen extremeties": "swollen extremities",
             "toxic look typhos": "toxic look (typhoid)", "spotting urination": "blood in urine",
             "belly pain": "belly pain", "foul smell of urine": "foul-smelling urine"}
    s = fixes.get(s, s)
    return s[:1].upper() + s[1:]


@lru_cache(maxsize=1)
def _descriptions() -> dict:
    p = KNOWLEDGE_DIR / "symptom_Description.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    return {_key(r.Disease): str(r.Description) for r in df.itertuples()}


@lru_cache(maxsize=1)
def _precautions() -> dict:
    p = KNOWLEDGE_DIR / "symptom_precaution.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    out = {}
    for r in df.itertuples(index=False):
        vals = [str(v).strip().capitalize().replace("Asprin", "Aspirin").replace("asprin", "aspirin")
                for v in r[1:] if isinstance(v, str) and v.strip()]
        out[_key(r[0])] = vals
    return out


@lru_cache(maxsize=1)
def _severity() -> dict:
    p = KNOWLEDGE_DIR / "Symptom-severity.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    return {str(r.Symptom).strip().replace(" ", "_"): int(r.weight) for r in df.itertuples()}


@lru_cache(maxsize=1)
def _profile() -> dict:
    p = KNOWLEDGE_DIR / "disease_symptom_profile.json"
    return json.loads(p.read_text()) if p.exists() else {}


def disease_description(label: str) -> str:
    return _descriptions().get(_key(label), "No description available for this condition.")


def disease_precautions(label: str) -> list:
    return _precautions().get(_key(label), [])


def severity_summary(symptoms: list) -> dict:
    """Total severity weight + qualitative band based on the dataset's symptom weights."""
    w = _severity()
    # keys in the severity CSV differ slightly from model features (spaces vs underscores)
    norm = {k.replace(" ", ""): v for k, v in w.items()}
    total = sum(norm.get(s.replace(" ", "").replace("_", "").strip(), 0) or w.get(s, 0) for s in symptoms)
    if not symptoms:
        return {"score": 0, "level": "None", "max": 0}
    avg = total / len(symptoms)
    if total < 12:
        level = "Mild"
    elif total < 26:
        level = "Moderate"
    else:
        level = "Severe"
    return {"score": int(total), "level": level, "avg": round(avg, 1)}


# ------------------------------------------------------------------ red flags
RED_FLAG_SYMPTOMS = {
    "chest_pain": "chest pain", "coma": "loss of consciousness", "altered_sensorium": "confusion / altered consciousness",
    "slurred_speech": "slurred speech", "weakness_of_one_body_side": "weakness on one side of the body",
    "blood_in_sputum": "coughing up blood", "stomach_bleeding": "gastrointestinal bleeding",
    "bloody_stool": "blood in stool", "acute_liver_failure": "signs of acute liver failure",
    "breathlessness": "difficulty breathing", "loss_of_balance": "sudden loss of balance",
}


def emergency_alerts(symptoms: list) -> list:
    """Return plain-language warnings when the symptom pattern may need urgent care."""
    s = set(symptoms)
    alerts = []
    cardiac_partners = {"sweating", "breathlessness", "vomiting", "nausea", "fast_heart_rate", "palpitations", "dizziness"}
    if "chest_pain" in s and s & cardiac_partners:
        alerts.append("Chest pain together with breathlessness, sweating, nausea or a racing heart can signal a "
                      "heart attack. Call your local emergency number right away.")
    if {"slurred_speech", "weakness_of_one_body_side"} & s:
        alerts.append("Slurred speech or one-sided weakness can be signs of a stroke. Seek emergency care immediately.")
    if {"coma", "altered_sensorium"} & s:
        alerts.append("Confusion or loss of consciousness needs urgent medical attention.")
    if {"blood_in_sputum", "stomach_bleeding", "bloody_stool"} & s:
        alerts.append("Bleeding symptoms should be evaluated by a doctor as soon as possible.")
    if "breathlessness" in s and not alerts:
        alerts.append("Difficulty breathing should not be ignored; see a doctor promptly if it is severe or sudden.")
    return alerts


# ------------------------------------------------------------ risk-page links
def risk_module_for(label: str):
    """Map a predicted disease to one of the structured risk assessments (or None)."""
    k = _key(label)
    if "diabetes" in k or "hypoglycemia" in k:
        return "diabetes"
    if "heart" in k or "hypertension" in k:
        return "heart"
    if any(x in k for x in ("hepatitis", "jaundice", "cholestasis", "liver")):
        return "liver"
    return None


# ------------------------------------------------------------- follow-up Qs
def suggest_followups(top_diseases: list, top_probs: list, current: list, k: int = 5) -> list:
    """Symptoms the person has NOT mentioned that are common in the leading conditions.
    Asking about them is the fastest way to separate look-alike diseases."""
    prof = _profile()
    have = set(current)
    score = {}
    for d, p in zip(top_diseases, top_probs):
        freqs = prof.get(d) or prof.get(str(d).strip()) or {}
        for sym, f in freqs.items():
            if sym in have or f < 0.35:
                continue
            score[sym] = score.get(sym, 0.0) + float(p) * f
    ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
    return [s for s, _ in ranked[:k]]
