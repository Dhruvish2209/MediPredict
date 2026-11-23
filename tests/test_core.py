"""Backend tests: run from the project root with   pytest -q"""
import sqlite3

import numpy as np
import pytest

from app.utils import auth, db
from app.utils.knowledge import clean_disease_name, emergency_alerts, risk_module_for, severity_summary
from app.utils.nlp import analyze_text
from app.utils.predict import load_model, predict_symptom, run_assessment, symptom_proba
from app.utils.report import build_risk_pdf, build_symptom_pdf
from app.utils.schemas import SPECS

FEATS = load_model("symptom")["features"]


# ----------------------------------------------------------------------- NLP
def test_nlp_basic_and_duration():
    r = analyze_text("high fever, headache and joint pain for 3 days", FEATS)
    assert {"high_fever", "headache", "joint_pain"} <= set(r["found"])
    assert r["duration"] == "3 days"


def test_nlp_negation():
    r = analyze_text("no fever but bad cough and sore throat", FEATS)
    assert "cough" in r["found"] and "throat_irritation" in r["found"]
    assert "high_fever" in r["negated"] and "high_fever" not in r["found"]
    r = analyze_text("I don't have a cough or headache, however I feel nauseous", FEATS)
    assert {"cough", "headache"} <= set(r["negated"]) and "nausea" in r["found"]


def test_nlp_no_substring_false_positives():
    assert analyze_text("took a photo in the gastric hall", FEATS)["found"] == []


def test_nlp_typos_and_blood_in_urine():
    assert "headache" in analyze_text("headake", FEATS)["found"]
    assert "spotting_ urination" in analyze_text("blood in urine", FEATS)["found"]


# --------------------------------------------------------- symptom classifier
def test_symptom_ensemble_handles_partial_input():
    top, probs = predict_symptom(["skin_rash", "high_fever", "joint_pain", "headache"])
    assert top[0].strip() == "Dengue"
    assert pytest.approx(sum(symptom_proba(["cough"])[0]), abs=1e-6) == 1.0


def test_knowledge_helpers():
    assert clean_disease_name("Diabetes ") == "Diabetes"
    assert risk_module_for("Heart attack") == "heart"
    assert emergency_alerts(["chest_pain", "sweating"])
    assert severity_summary(["high_fever", "chest_pain"])["score"] > 0


# ---------------------------------------------------------------- risk models
@pytest.mark.parametrize("name", ["diabetes", "heart", "liver"])
def test_assessment_shap_is_additive_and_ordered(name):
    spec = SPECS[name]
    healthy = run_assessment(name, spec.presets["Healthy example"])
    risky = run_assessment(name, spec.presets["High-risk example"])
    assert risky["risk_pct"] > healthy["risk_pct"]
    assert risky["level"] == "HIGH" and healthy["level"] == "LOW"
    for r in (healthy, risky):
        assert r["additivity_gap"] < 1.0, "base + sum(SHAP) must reproduce the prediction"
        assert any(abs(f["contribution"]) > 0.5 for f in r["factors"]), "SHAP must not be all zeros (old bug)"


def test_unknown_values_use_imputer():
    v = dict(SPECS["diabetes"].presets["High-risk example"], Insulin=None, SkinThickness=None)
    r = run_assessment("diabetes", v)
    assert set(r["unknown"]) == {"2-hour Serum Insulin", "Triceps Skin-fold Thickness"}
    assert 0 <= r["risk_pct"] <= 100


def test_out_of_range_warning():
    v = dict(SPECS["heart"].presets["Healthy example"], Cholesterol=640)
    assert run_assessment("heart", v)["warnings"]


# ------------------------------------------------------------------------ auth
def test_auth_flow_and_lockout():
    db.init_db()
    uid, err = auth.register("Test", "t@example.com", "Passw0rd1")
    assert uid and not err
    assert auth.register("Test", "t@example.com", "Passw0rd1")[1]            # duplicate
    assert auth.register("X", "bad-email", "Passw0rd1")[1]
    assert auth.register("X", "x@example.com", "short")[1]
    assert auth.register("Doc", "d@example.com", "Passw0rd1", "doctor", "wrong")[1]   # needs invite code
    assert auth.login("t@example.com", "Passw0rd1")[0]
    for _ in range(5):
        auth.login("t@example.com", "nope")
    assert "Too many" in auth.login("t@example.com", "Passw0rd1")[1]


def test_prediction_roundtrip_and_privacy():
    uid = db.get_user_by_email("t@example.com")["user_id"]
    pid = db.save_prediction(uid, "Heart Disease", 80, "HIGH", {"Age": 50}, "risk", "SVM", {"factors": []})
    assert db.get_prediction(pid)["input_params"] == {"Age": 50}
    assert any(p["pred_id"] == pid for p in db.get_all_predictions())
    db.update_user(uid, share_with_doctors=0)
    assert not any(p["pred_id"] == pid for p in db.get_all_predictions())
    db.delete_prediction(pid, uid)
    assert db.get_prediction(pid) is None


def test_v1_database_migrates(tmp_path, monkeypatch):
    """A database made by the original project must keep working."""
    p = tmp_path / "old.db"
    c = sqlite3.connect(p)
    c.executescript("""CREATE TABLE users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE,
        password_hash TEXT, role TEXT DEFAULT 'patient', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE predictions (pred_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, disease TEXT,
        risk_score REAL, risk_level TEXT, input_params TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO users (name,email,password_hash) VALUES ('Old','o@x.com','h');
        INSERT INTO predictions (user_id,disease,risk_score,risk_level,input_params) VALUES (1,'hepatitis A ',65,'HIGH','{"symptoms": ["itching"]}');""")
    c.commit(); c.close()
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db()
    row = db.get_user_history(1)[0]
    assert row["kind"] == "symptom" and row["disease"] == "Hepatitis A"


# --------------------------------------------------------------------- reports
def test_pdf_reports_build():
    r = run_assessment("liver", SPECS["liver"].presets["High-risk example"])
    assert build_risk_pdf({"name": "A"}, r)[:4] == b"%PDF"
    top, probs = predict_symptom(["itching", "skin_rash"])
    assert build_symptom_pdf({"name": "A"}, {"symptoms": ["itching"], "top": list(zip(top, probs)), "severity": {}, "alerts": []})[:4] == b"%PDF"
