# 🩺 MediPredict

An explainable AI health-screening app built with Streamlit. Describe symptoms in plain words, or enter lab values, and get a
risk estimate **together with an explanation of what drove it**.

> Educational project. Not a medical device and not a substitute for a clinician.

## ✨ Features

| Area | What you get |
| --- | --- |
| **Symptom Checker** | Free-text NLP (negation-aware, typo-tolerant, extracts durations), pick-from-list chips, top-3 conditions with descriptions & precautions, severity score, red-flag emergency alerts, "Do you also have…?" follow-ups that refine the result, symptom-impact chart, PDF report |
| **Diabetes / Heart / Liver risk** | Schema-driven forms with live reference-range chips, "I don't know" for optional labs (handled by the trained imputer), example profiles, BMI calculator, out-of-range warnings |
| **Explainability** | Correct SHAP in *percentage points of risk*: interactive bar chart, waterfall, your-values-vs-dataset table (percentiles), **what-if simulator**, personalised guidance, PDF report |
| **Dashboard & History** | KPIs, risk gauges, trends, filters, CSV export, full stored explanation for every past result, delete |
| **Doctor Panel** | Triage queue of high-risk cases, patient directory, analytics, clinical notes the patient can read, CSV export |
| **Accounts & privacy** | bcrypt hashes, password rules, brute-force lockout, doctor invitation code, per-user "share with doctors" switch, data export, delete account |
| **Model Insights** | How it works, metrics, ROC/confusion matrices, global SHAP, robustness tests, honest limitations |
| **UI** | Custom design system, light/dark aware, responsive down to phones, Material icons |

## 🚀 Quick start

**Windows PowerShell** (choose a Python version installed on your computer):

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set a private DOCTOR_INVITE_CODE before enabling doctor registration.
.\.venv\Scripts\python.exe scripts/seed_demo.py  # optional demo users and sample history
.\.venv\Scripts\python.exe -m streamlit run app/main.py
```

**macOS / Linux:** create and activate a virtual environment with `python3 -m venv .venv`, install dependencies with
`python -m pip install -r requirements.txt`, copy `.env.example` to `.env`, set a private `DOCTOR_INVITE_CODE`, then run
`python scripts/seed_demo.py` (optional) and `streamlit run app/main.py`.

Demo accounts (created by `seed_demo.py`; delete before real use):

| Role | Email | Password |
| --- | --- | --- |
| Patient | `demo.patient@medipredict.app` | `Demo@1234` |
| Doctor | `demo.doctor@medipredict.app` | `Doctor@1234` |

To register a **doctor** account, set a private invitation code in `.env`. Doctor registration is disabled until configured.
The demo seeder creates a sample doctor account directly; keep demo accounts and sample records out of any real deployment.

Your existing `database/medipredict.db` keeps working: new columns/tables are added automatically on first start.

## 🧪 Tests

```bash
pytest -q tests          # 19 tests: NLP, SHAP additivity, auth, DB migration, PDFs, every chart builder
```

## 🔧 What changed in the backend (and why)

1. **SHAP was producing all zeros.** The old code used the *single row being explained* as the SHAP background, so every
   feature already equalled its "average". The new `shap_utils.py` uses a stratified sample of the real training data and
   explains the **probability** output for every model (LR / SVM / trees), so contributions are in percentage points and add up
   exactly: `average-patient risk + Σ contributions = your risk` (verified by tests). One-hot columns are merged back into
   the form fields people recognise (e.g. *Chest Pain Type*).
2. **Symptom model is an ensemble.** XGBoost was trained on *complete* symptom lists and is erratic when a user types 3–5
   symptoms (fever + headache + joint pain + rash ranked *Impetigo* first). It is now averaged with a symptom-profile
   Naive-Bayes model: top-1 accuracy with 4 reported symptoms rises from ~80 % to ~96 %
   (`python scripts/benchmark_symptom_ensemble.py`). Both models are fitted on the same synthetic data, so use this to compare
   methods, not as real-world accuracy.
3. **NLP:** word-boundary matching (no more "gas" ⊂ "gastric"), negation ("no fever"), durations, typo tolerance, and synonyms
   for the 72 symptoms that previously had none. Fixed mappings that pointed to non-existent features (`spotting_ urination`
   has a space in the model's feature list, so "blood in urine" never worked).
4. **Data quality:** the training imputer is now actually used (optional labs can be "unknown"), and inputs outside the training
   range raise a warning.
5. **No duplicate history rows** (the old page saved on every Streamlit rerun); refining a symptom analysis updates the same record.
6. **Security:** doctor accounts need an invitation code; lockout after 5 failed logins; patients can opt out of doctor visibility.
7. **Runtime no longer needs `data/`:** `scripts/build_assets.py` writes small derived files to `app/assets/` (SHAP background,
   reference percentiles, symptom profiles, descriptions/precautions), so the app deploys without the large CSVs.
8. **Dependency fix:** the models were pickled with scikit-learn **1.7.2**, but `requirements.txt` pinned 1.3.2. Now corrected.

## 🗂️ Structure

```
app/
  main.py                 router + role-aware navigation + sidebar
  views/                  login, dashboard, symptoms, diabetes/heart/liver (one-liners), risk_common,
                          history, detail, doctor_panel, insights, profile
  utils/
    config.py db.py auth.py session.py          app plumbing
    nlp.py synonyms.py knowledge.py             symptom understanding & medical knowledge
    schemas.py                                  declarative form/feature spec for each risk model
    predict.py shap_utils.py recommend.py       models, explanations, guidance
    report.py ui.py timefmt.py                  PDF, design system & charts, time helpers
  assets/                   logo, SHAP backgrounds, reference stats, knowledge tables
scripts/                    build_assets.py, seed_demo.py, benchmark_symptom_ensemble.py
tests/                      pytest suite
models/ reports/ notebooks/ data/   (unchanged)
```

**Add another disease model:** train it, save `{name}_model/scaler/imputer/features/model_name.pkl` in `models/`, add a
`DiseaseSpec` in `utils/schemas.py`, run `scripts/build_assets.py`, and add a one-line page like `views/heart.py`.

## ☁️ Deploying (Streamlit Cloud)

Commit `models/*.pkl`, `reports/*.png|csv` and `app/assets/` (the `.gitignore` already allows them), set `DOCTOR_INVITE_CODE`
in the app's secrets/environment, and point the app at `app/main.py`. SQLite on Streamlit Cloud is ephemeral: for persistent
data mount a volume and set `MEDIPREDICT_DB`, or move to a hosted database.

## 🩹 Troubleshooting

- **Plotly `ValueError: Invalid property ... 'cornerradius'`:** fixed in this version (code now works on Plotly 5.18 and newer).
- **Model-loading warnings:** keep the pinned `scikit-learn==1.7.2` (the models were saved with it). XGBoost prints a harmless
  "serialized model" notice when unpickling.
- **Fonts/icons look plain offline:** the UI loads Inter / Plus Jakarta Sans from Google Fonts; without internet it falls back to system fonts.

## ⚠️ Known limitations

- Models are trained on small public datasets and are not clinically validated; the PIMA data covers women of Pima heritage.
- The symptom dataset is synthetic (fixed symptom sets per disease), so very high accuracies there don't transfer to real patients.
- Streamlit sessions are per-browser-tab: a full page reload signs you out (use the sidebar to navigate).
- Probabilities from SVM/LR are model scores, not calibrated clinical risks.

## 📦 Datasets

See `data/raw/SOURCES.md`. Kaggle: disease-symptom description (4,920 rows), PIMA Indians Diabetes (768),
Heart Failure Prediction (918), Indian Liver Patient (583).
