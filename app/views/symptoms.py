from datetime import datetime

import streamlit as st

from app.utils import db, ui
from app.utils.knowledge import (clean_disease_name, disease_description, disease_precautions, emergency_alerts,
                                 pretty_symptom, risk_module_for, severity_summary, suggest_followups)
from app.utils.nlp import analyze_text
from app.utils.predict import confidence_band, load_model, predict_symptom, symptom_impact
from app.utils.report import build_symptom_pdf
from app.utils.session import require_login

user = require_login()
art = load_model("symptom")
canonical = art["features"]
RES = "sym:result"
COMMON = ["high_fever", "headache", "cough", "fatigue", "nausea", "vomiting", "chest_pain", "breathlessness",
          "joint_pain", "skin_rash", "abdominal_pain", "dizziness", "chills", "sweating", "diarrhoea", "itching",
          "muscle_pain", "loss_of_appetite", "yellowish_skin", "weight_loss"]
EXAMPLES = ["I have had high fever, headache and joint pain for 3 days, with a skin rash",
            "Chest pain, sweating and shortness of breath, my heart is racing",
            "Always thirsty, peeing a lot, blurred vision and tired. No fever",
            "Yellow eyes, dark urine, loss of appetite and nausea"]


def run_analysis(symptoms, meta, refine=False):
    negated = meta.get("negated", [])
    top, probs = predict_symptom(symptoms, k=3, negated=negated)
    impact = symptom_impact(symptoms, negated)
    sev = severity_summary(symptoms)
    alerts = emergency_alerts(symptoms)
    prev = st.session_state.get(RES)
    name, conf = clean_disease_name(top[0]), probs[0]
    payload = {"symptoms": symptoms, "top3": [(clean_disease_name(t), p) for t, p in zip(top, probs)],
               "duration": meta.get("duration"), "negated": meta.get("negated", []), "severity": sev}
    expl = {"impact": impact[:8], "alerts": alerts}
    if refine and prev and prev.get("pred_id"):
        pid = prev["pred_id"]
        db.update_prediction(pid, name, conf * 100, confidence_band(conf), payload, art["name"], expl)
    else:
        pid = db.save_prediction(user["user_id"], name, conf * 100, confidence_band(conf), payload, kind="symptom",
                                 model_name=str(art["name"]), explanation=expl)
    st.session_state[RES] = {"symptoms": symptoms, "top": top, "probs": probs, "impact": impact, "severity": sev,
                             "alerts": alerts, "pred_id": pid, **meta}


def analyse_text_click():
    text = st.session_state.get("sym_text", "")
    if not text.strip():
        st.session_state["sym_msg"] = ("warning", "Please describe your symptoms first.")
        return
    a = analyze_text(text, canonical)
    if not a["found"]:
        st.session_state["sym_msg"] = ("error", "I couldn't recognise any symptoms. Try different wording or use the 'Pick symptoms' tab.")
        return
    st.session_state["sym_msg"] = None
    st.session_state["sym_edit"] = a["found"]
    run_analysis(a["found"], {"duration": a["duration"], "negated": a["negated"], "evidence": a["evidence"], "source": "text"})


def analyse_pick_click():
    picked = sorted(set(st.session_state.get("sym_pick", [])) | set(st.session_state.get("sym_pills") or []))
    if len(picked) < 1:
        st.session_state["sym_msg"] = ("warning", "Select at least one symptom.")
        return
    st.session_state["sym_msg"] = None
    st.session_state["sym_edit"] = picked
    run_analysis(picked, {"duration": None, "negated": [], "evidence": {}, "source": "list"})


def refine_click(extra=()):
    syms = sorted(set(st.session_state.get("sym_edit", [])) | set(extra))
    if not syms:
        return
    st.session_state["sym_edit"] = syms
    prev = st.session_state.get(RES, {})
    run_analysis(syms, {"duration": prev.get("duration"), "negated": prev.get("negated", []),
                        "evidence": prev.get("evidence", {}), "source": "refine"}, refine=True)


def set_example(txt):
    st.session_state["sym_text"] = txt


ui.page_header("Symptom Checker", "Tell me how you feel. Natural language is fine: 'no fever but a bad cough for 2 days'.",
               "stethoscope", chips=["NLP symptom extraction", "41 conditions", "Handles negation"])
st.write("")

with st.container(border=True):
    t1, t2 = st.tabs(["Describe in words", "Pick symptoms"])
    with t1:
        st.text_area("How are you feeling?", key="sym_text", height=110,
                     placeholder="e.g. I've had a high fever, headache and joint pain for 3 days, but no cough")
        st.markdown("<div class='mp-muted' style='font-size:.8rem;margin-bottom:.3rem'>Try an example:</div>", unsafe_allow_html=True)
        ecols = st.columns(len(EXAMPLES))
        for i, (c, ex) in enumerate(zip(ecols, EXAMPLES)):
            c.button(ex.split(",")[0][:34] + "…", key=f"ex{i}", on_click=set_example, args=(ex,), width="stretch", help=ex)
        st.button("Analyse symptoms", type="primary", icon=":material/search_insights:", on_click=analyse_text_click,
                  width="stretch", key="go_text")
    with t2:
        st.pills("Common symptoms", COMMON, selection_mode="multi", key="sym_pills", format_func=pretty_symptom)
        st.multiselect("…or search all 131 symptoms", canonical, key="sym_pick", format_func=pretty_symptom,
                       placeholder="Start typing, e.g. 'knee pain'")
        st.button("Analyse symptoms", type="primary", icon=":material/search_insights:", on_click=analyse_pick_click,
                  width="stretch", key="go_pick")

msg = st.session_state.get("sym_msg")
if msg:
    getattr(st, msg[0])(msg[1])

res = st.session_state.get(RES)
if not res:
    st.write("")
    ui.callout("brand", "Your analysis will appear here",
               "You'll see the most likely conditions, what drove them, precautions, and smart follow-up questions.")
    st.write("")
    ui.disclaimer()
    st.stop()

# ----------------------------------------------------------------- results
st.divider()
for a in res["alerts"]:
    ui.callout("alert", "Seek urgent medical care", a)
if len(res["symptoms"]) < 3:
    ui.callout("warn", "Add more symptoms for a reliable result",
               "With fewer than 3 symptoms many conditions look alike. Answer the follow-up questions below to narrow it down.")
if res["probs"][0] < 0.3:
    ui.callout("info", "Low confidence", "No single condition stands out. Adding more symptoms usually helps.")

left, right = st.columns([1, 1.5], gap="large")
with left:
    ui.section("What I understood", "", "hearing", "brand")
    chips = "".join(f"<span class='mp-sym'>{pretty_symptom(s)}</span>" for s in res["symptoms"])
    chips += "".join(f"<span class='mp-sym neg'>{pretty_symptom(s)}</span>" for s in res.get("negated", []) if s not in res["symptoms"])
    if res.get("duration"):
        chips += f"<span class='mp-chip' style='margin-bottom:.4rem'>{ui.icon('schedule', 14)} {res['duration']}</span>"
    st.markdown(ui.html(f"<div class='mp-card'>{chips}</div>"), unsafe_allow_html=True)
    if res.get("negated"):
        st.caption("Struck-through symptoms were mentioned as absent and are not used.")

    sev = res["severity"]
    tone = {"Mild": "good", "Moderate": "warn", "Severe": "alert"}.get(sev["level"], "info")
    st.markdown(ui.html(f"""<div class='mp-card' style='margin-top:.8rem'><div class='mp-kpi'>
        <div class='ic' style='background:{ui.soft(tone)}'>{ui.icon('vital_signs', 24, ui.TONES[tone][0])}</div>
        <div><div class='lbl'>Symptom severity</div><div class='val'>{sev['level']}</div>
        <div class='sub'>Score {sev['score']} from dataset symptom weights</div></div></div></div>"""), unsafe_allow_html=True)

    with st.expander("Edit symptoms & re-run", icon=":material/edit:", expanded=False):
        st.multiselect("Symptoms used", canonical, key="sym_edit", format_func=pretty_symptom)
        st.button("Re-run analysis", icon=":material/refresh:", on_click=refine_click, width="stretch", key="rerun")

with right:
    ui.section("Most likely conditions", "Ranked by model confidence", "leaderboard", "violet")
    for i, (lab, p) in enumerate(zip(res["top"], res["probs"])):
        name = clean_disease_name(lab)
        color = "#4f46e5" if i == 0 else "#94a3b8"
        with st.container(border=True):
            st.markdown(ui.html(f"""<div style='display:flex;justify-content:space-between;align-items:center;gap:.6rem'>
                <div style='font-weight:700;font-size:1.05rem'><span class='mp-chip' style='margin-right:.4rem'>#{i + 1}</span>{name}</div>
                <div style='font-family:Plus Jakarta Sans;font-weight:800;font-size:1.25rem;color:{color}'>{p * 100:.1f}%</div></div>
                <div style='margin-top:.5rem'>{ui.bar_html(p * 100, color)}</div>"""), unsafe_allow_html=True)
            with st.expander("About & precautions", expanded=(i == 0)):
                st.write(disease_description(lab))
                prec = disease_precautions(lab)
                if prec:
                    st.markdown("**Suggested precautions**\n" + "\n".join(f"- {x}" for x in prec))
                mod = risk_module_for(lab)
                if mod:
                    st.page_link(f"views/{mod}.py", icon=":material/arrow_forward:",
                                 label=f"Run the detailed {mod} risk assessment with lab values")

st.write("")
c1, c2 = st.columns([1.5, 1], gap="large")
with c1:
    ui.section("What drove the top prediction?", f"Effect of each symptom on {clean_disease_name(res['top'][0])}", "psychology", "brand")
    with st.container(border=True):
        ui.show(ui.impact_chart([(pretty_symptom(s), v) for s, v in res["impact"]]), key="sym_impact")
        st.caption("Computed by removing each symptom in turn and measuring how much the top condition's probability drops. "
                   "Probabilities blend XGBoost with a symptom-profile (Naive Bayes) model, which stays reliable when you report only a few symptoms.")
with c2:
    ui.section("Help me narrow it down", "Do you also have…", "quiz", "violet")
    follow = suggest_followups(res["top"], res["probs"], res["symptoms"])
    with st.container(border=True):
        if follow:
            st.pills("Tap any that apply", follow, selection_mode="multi", key="sym_follow", format_func=pretty_symptom)
            st.button("Add & update analysis", type="primary", icon=":material/add_circle:", width="stretch", key="addf",
                      on_click=lambda: (st.session_state.__setitem__("sym_edit", res["symptoms"]),
                                        refine_click(st.session_state.get("sym_follow") or [])))
        else:
            st.write("No further questions. Your symptom list already covers the common signs.")
    st.download_button("Download PDF report", icon=":material/picture_as_pdf:", width="stretch", key="sym_pdf",
                       data=build_symptom_pdf(user, {"symptoms": res["symptoms"], "top": list(zip(res["top"], res["probs"])),
                                                     "severity": res["severity"], "duration": res.get("duration"), "alerts": res["alerts"]}),
                       mime="application/pdf", file_name=f"MediPredict_Symptoms_{datetime.now():%Y%m%d_%H%M}.pdf")
    st.caption("Saved to your history automatically.")
st.write("")
ui.disclaimer()
