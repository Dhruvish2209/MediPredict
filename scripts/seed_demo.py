"""
Create demo accounts and realistic sample history so you can showcase every feature immediately.

    python scripts/seed_demo.py            # adds demo data (safe to re-run)

Accounts created (change/delete them before any real use):
    patient : demo.patient@medipredict.app / Demo@1234
    doctor  : demo.doctor@medipredict.app  / Doctor@1234
"""
import random
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils import auth, db  # noqa: E402
from app.utils.knowledge import clean_disease_name  # noqa: E402
from app.utils.predict import confidence_band, predict_symptom, run_assessment  # noqa: E402
from app.utils.schemas import SPECS  # noqa: E402

db.init_db()
rng = random.Random(7)
PEOPLE = [("Demo Patient", "demo.patient@medipredict.app", "Demo@1234", "patient", 41, "Male"),
          ("Aarav Shah", "aarav@example.com", "Demo@1234", "patient", 52, "Male"),
          ("Meera Patel", "meera@example.com", "Demo@1234", "patient", 34, "Female"),
          ("Rohan Verma", "rohan@example.com", "Demo@1234", "patient", 63, "Male"),
          ("Dr. Anita Rao", "demo.doctor@medipredict.app", "Doctor@1234", "doctor", 45, "Female")]
SYMPTOM_SETS = [["high_fever", "headache", "joint_pain", "skin_rash", "chills"], ["cough", "breathlessness", "chest_pain", "fatigue"],
                ["polyuria", "excessive_hunger", "fatigue", "blurred_and_distorted_vision"], ["yellowish_skin", "dark_urine", "nausea", "loss_of_appetite"]]


def backdate(pred_id, days):
    ts = (datetime.utcnow() - timedelta(days=days, hours=rng.randint(0, 8))).strftime("%Y-%m-%d %H:%M:%S")
    with db.get_conn() as c:
        c.execute("UPDATE predictions SET created_at=? WHERE pred_id=?", (ts, pred_id))


def jitter(vals, spec):
    out = dict(vals)
    for f in spec.fields:
        if f.kind == "number" and out.get(f.key) is not None:
            v = out[f.key] * rng.uniform(0.9, 1.1)
            v = max(f.min, min(f.max, v))
            out[f.key] = int(round(v)) if f.is_int else round(v, 2)
    return out


for name, email, pw, role, age, sex in PEOPLE:
    user = db.get_user_by_email(email)
    if user:
        continue
    uid = db.create_user(name, email, auth.hash_password(pw), role, age, sex)
    if role != "patient":
        continue
    for i in range(rng.randint(3, 6)):
        days = rng.randint(1, 60)
        if rng.random() < 0.35:
            syms = rng.choice(SYMPTOM_SETS)
            top, probs = predict_symptom(syms, 3)
            payload = {"symptoms": syms, "top3": [(clean_disease_name(t), p) for t, p in zip(top, probs)]}
            pid = db.save_prediction(uid, clean_disease_name(top[0]), probs[0] * 100, confidence_band(probs[0]), payload, "symptom", "Ensemble")
        else:
            key = rng.choice(list(SPECS))
            spec = SPECS[key]
            base = spec.presets["High-risk example" if (name != "Demo Patient" and rng.random() < 0.6) else "Healthy example"]
            r = run_assessment(key, jitter(base, spec))
            pid = db.save_prediction(uid, spec.short, r["risk_pct"], r["level"], r["ui_values"], "risk", r["model_name"],
                                     {k: r[k] for k in ("base_pct", "factors", "comparison", "warnings", "unknown", "model_name", "disease")})
        backdate(pid, days)
    print("created", name)
print("Done. Log in with the accounts listed at the top of this file.")
