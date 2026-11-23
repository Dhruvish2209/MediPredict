"""Render one saved prediction (used by History and the Doctor Panel)."""
import pandas as pd
import streamlit as st

from app.utils import ui
from app.utils.knowledge import clean_disease_name, disease_description, disease_precautions, pretty_symptom, risk_module_for
from app.utils.report import build_symptom_pdf
from app.views.risk_common import render_result


def to_result(rec):
    ex = rec.get("explanation")
    if rec.get("kind") != "risk" or not isinstance(ex, dict) or not ex.get("factors"):
        return None
    from app.utils.schemas import SPECS
    name = ex.get("disease") or next((k for k, s in SPECS.items() if s.short == rec["disease"]), None)
    if not name:
        return None
    return {"disease": name, "title": rec["disease"], "risk_pct": rec["risk_score"], "level": rec["risk_level"],
            "model_name": ex.get("model_name", rec.get("model_name") or "–"), "base_pct": ex["base_pct"],
            "ui_values": rec["input_params"], "factors": ex["factors"], "comparison": ex.get("comparison", []),
            "warnings": ex.get("warnings", []), "unknown": ex.get("unknown", []), "pred_id": rec["pred_id"]}


def render_detail(rec, viewer, patient, prefix):
    """viewer = signed-in user; patient = dict(name, age, sex) used on the PDF."""
    if rec.get("kind") == "symptom":
        p = rec["input_params"] if isinstance(rec["input_params"], dict) else {}
        syms = p.get("symptoms", [])
        st.markdown("".join(f"<span class='mp-sym'>{pretty_symptom(s)}</span>" for s in syms), unsafe_allow_html=True)
        top3 = p.get("top3", [])
        for i, (lab, prob) in enumerate(top3):
            st.markdown(ui.html(f"<div class='mp-row'><div><b>#{i + 1} {lab}</b></div><div>{prob * 100:.1f}%</div></div>"), unsafe_allow_html=True)
        if top3:
            st.write(disease_description(top3[0][0]))
            prec = disease_precautions(top3[0][0])
            if prec:
                st.markdown("**Precautions:** " + "; ".join(prec))
        ex = rec.get("explanation")
        if isinstance(ex, dict) and ex.get("impact"):
            ui.show(ui.impact_chart([(pretty_symptom(x[0]), x[1]) for x in ex["impact"]]), key=f"{prefix}:imp:{rec['pred_id']}")
        if top3:
            st.download_button("Download PDF", icon=":material/picture_as_pdf:", key=f"{prefix}:spdf:{rec['pred_id']}",
                               data=build_symptom_pdf(patient, {"symptoms": syms, "top": [(a, b) for a, b in top3],
                                                                "severity": p.get("severity"), "duration": p.get("duration"),
                                                                "alerts": (ex or {}).get("alerts", []) if isinstance(ex, dict) else []}),
                               mime="application/pdf", file_name=f"MediPredict_Symptoms_{rec['pred_id']}.pdf")
        return
    result = to_result(rec)
    if result:
        render_result(result, patient, f"{prefix}:{rec['pred_id']}", interactive=False)
    else:
        st.info("This record was saved by an earlier version and has no stored explanation. Showing the raw inputs.")
        params = rec.get("input_params")
        if isinstance(params, dict):
            st.dataframe(pd.DataFrame({"Field": list(params), "Value": [str(v) for v in params.values()]}), hide_index=True, width="stretch")
