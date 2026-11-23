import pandas as pd
import streamlit as st

from app.utils import ui
from app.utils.config import REPORTS_DIR
from app.utils.predict import load_model, load_reference
from app.utils.schemas import SPECS
from app.utils.session import require_login

require_login()
ui.page_header("Model Insights", "How MediPredict works, how well each model performs, and what drives its decisions.", "science",
               chips=["Transparent by design", "Metrics from your training notebooks"])
st.write("")

ui.section("How it works", "Two-stage explainable pipeline", "account_tree")
steps = [("Understand", "NLP turns free text into canonical symptoms: negation-aware, typo-tolerant."),
         ("Predict", "XGBoost + a symptom-profile model rank 41 conditions; SVM / Logistic models score disease risk."),
         ("Explain", "SHAP on the probability output shows each factor's push in percentage points."),
         ("Act", "Personalised guidance, what-if simulation, history and PDF reports.")]
cols = st.columns(4, gap="medium")
for i, (c, (t, d)) in enumerate(zip(cols, steps), 1):
    c.markdown(ui.html(f"<div class='mp-card' style='height:100%'><div class='mp-step'><div class='n'>{i}</div><div><b>{t}</b><div class='mp-muted' style='font-size:.85rem;margin-top:.2rem'>{d}</div></div></div></div>"), unsafe_allow_html=True)
st.write("")


def img(path, caption=None):
    p = REPORTS_DIR / path
    if p.exists():
        st.image(str(p), caption=caption, width="stretch")
    else:
        st.caption(f"({path} not found: re-run the notebooks to regenerate it)")


def table(csv, selected=None):
    p = REPORTS_DIR / csv
    if not p.exists():
        return
    d = pd.read_csv(p)
    if selected is not None and "Model" in d:
        d.insert(0, "In use", d["Model"].map(lambda m: "✔" if m == selected else ""))
    cfg = {c: st.column_config.ProgressColumn(c, min_value=0, max_value=1, format="%.3f") for c in d.columns
           if c in ("Accuracy", "Precision", "Recall", "F1", "ROC-AUC")}
    st.dataframe(d, hide_index=True, width="stretch", column_config=cfg)


tabs = st.tabs(["Symptom classifier", "Diabetes", "Heart", "Liver", "Data & limits"])

with tabs[0]:
    a = load_model("symptom")
    ui.kpi_cards([dict(label="Model in use", value=str(a["name"]).split(" (")[0], sub=str(a["name"]), icon="memory", tone="brand"),
                  dict(label="Conditions", value=len(a["le"].classes_), sub="Output classes", icon="category", tone="violet"),
                  dict(label="Symptoms", value=len(a["features"]), sub="Binary input features", icon="checklist", tone="info")])
    st.write("")
    ui.callout("warn", "Read the scores with care",
               "The symptom dataset is synthetic: every disease has a fixed symptom set, so clean-data accuracy reaches 100%. "
               "The noise and symptom-dropout tests below are a better guide to how it behaves with real, imperfect input.", "balance")
    st.write("")
    st.markdown("**Baseline comparison (complete symptom patterns)**")
    table("symptom_baseline_comparison.csv", "XGBoost")
    bp = REPORTS_DIR / "symptom_ensemble_benchmark.csv"
    if bp.exists():
        st.markdown("**Why the app uses an ensemble: accuracy when only a few symptoms are reported**")
        bm = pd.read_csv(bp)
        import plotly.express as px
        fig = px.line(bm, x="Symptoms reported", y="Top-1 accuracy", color="Model", markers=True,
                      color_discrete_map={"XGBoost": "#f59e0b", "Profile (Naive Bayes)": "#0ea5e9", "Ensemble (used in app)": "#4f46e5"})
        fig.update_traces(line=dict(width=3), marker=dict(size=8))
        fig.update_yaxes(range=[0.6, 1.01], tickformat=".0%", gridcolor=ui.tokens()["grid"])
        fig.update_xaxes(gridcolor=ui.tokens()["grid"], dtick=1)
        fig.update_layout(legend=dict(orientation="h", y=-0.25, title=None))
        with st.container(border=True):
            ui.show(ui._layout(fig, 340), key="ens_bench")
        st.caption("XGBoost was trained on complete symptom sets, so it is erratic with 3 – 5 symptoms. Averaging it with a "
                   "symptom-profile Naive Bayes model fixes that. Both are fitted on the same synthetic data, so use this to "
                   "compare methods, not as real-world accuracy. Reproduce with scripts/benchmark_symptom_ensemble.py.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**Robustness: injected noise**")
        img("robustness_noise_injection.png")
    with c2:
        st.markdown("**Robustness: dropped symptoms**")
        img("robustness_symptom_dropout.png")
    with st.expander("Confusion matrix & SHAP for the symptom model"):
        img("symptom_confusion_matrix.png")
        img("shap/symptom_bar_Dengue.png")

for tab, key in zip(tabs[1:4], ["diabetes", "heart", "liver"]):
    with tab:
        spec, a, ref = SPECS[key], load_model(key), load_reference(key)
        ui.kpi_cards([dict(label="Model in use", value=str(a["name"]).split(" (")[0], sub=str(a["name"]), icon="memory", tone="brand"),
                      dict(label="Training rows", value=ref.get("n_rows", "–"), sub=spec.dataset.split(" · ")[0], icon="dataset", tone="violet"),
                      dict(label="Prevalence", value=f"{(ref.get('prevalence') or 0) * 100:.0f}%", sub="Positive cases in data", icon="percent", tone="warn"),
                      dict(label="Features", value=len(a["features"]), sub="Model inputs", icon="tune", tone="info")])
        st.write("")
        st.markdown("**Model comparison (held-out test set)**")
        table(f"{key}_comparison.csv", str(a["name"]))
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("**ROC curves**")
            img(f"{key}_roc_curves.png")
        with c2:
            st.markdown("**Confusion matrix**")
            img(f"{key}_confusion_matrix.png")
        st.markdown("**Global SHAP importance**")
        s1, s2 = st.columns(2, gap="large")
        with s1:
            img(f"shap/{key}_bar.png")
        with s2:
            img(f"shap/{key}_summary.png")

with tabs[4]:
    st.markdown("""
**Data sources:** Kaggle disease-symptom dataset (4,920 rows), PIMA Indians Diabetes (768), Heart Failure Prediction (918) and Indian Liver Patient (583).

**Known limitations**
- Models are trained on small public datasets and are not clinically validated.
- PIMA covers women of Pima heritage aged 21 and over, so estimates for other groups are less reliable.
- The liver dataset is imbalanced (≈ 71% positive); risk percentages are model scores, not true probabilities.
- Out-of-range inputs trigger a warning because the model would be extrapolating.

**Explainability:** SHAP values are computed on the *probability* output with a background of real training patients,
so contributions are in percentage points and add up exactly from the average patient to your estimate.
""")
    ui.disclaimer()
