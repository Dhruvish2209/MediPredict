from datetime import datetime

import pandas as pd
import streamlit as st

from app.utils import db, ui
from app.utils.session import require_login
from app.utils.timefmt import ago, to_local

user = require_login()
hist = db.get_user_history(user["user_id"])
df = pd.DataFrame(hist)

hour = datetime.now().hour
greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
first = user["name"].split()[0]
ui.page_header(f"{greet}, {first} 👋", "Here is a snapshot of your health screening activity.", "dashboard",
               chips=["Doctor account" if user["role"] == "doctor" else "Patient account", f"{len(hist)} saved results"])
st.write("")

if df.empty:
    kpi = [dict(label="Assessments", value="0", sub="Nothing yet", icon="assignment", tone="brand"),
           dict(label="High-risk flags", value="0", sub="All clear", icon="shield", tone="good"),
           dict(label="Last check-up", value="–", sub="Start your first one", icon="schedule", tone="violet"),
           dict(label="Average risk", value="–", sub="No data", icon="monitor_heart", tone="info")]
else:
    df["created_at"] = df["created_at"].astype(str)
    high = int((df["risk_level"] == "HIGH").sum())
    risk_df = df[df["kind"] == "risk"] if "kind" in df else df
    avg = f"{risk_df['risk_score'].mean():.0f}%" if not risk_df.empty else "–"
    kpi = [dict(label="Assessments", value=len(df), sub=f"{(df['kind'] == 'symptom').sum()} symptom · {len(risk_df)} risk", icon="assignment", tone="brand"),
           dict(label="High-risk flags", value=high, sub="Worth discussing with a doctor" if high else "All clear", icon="warning" if high else "shield", tone="alert" if high else "good"),
           dict(label="Last check-up", value=ago(df.iloc[0]["created_at"]), sub=df.iloc[0]["disease"], icon="schedule", tone="violet"),
           dict(label="Average risk", value=avg, sub="Across structured assessments", icon="monitor_heart", tone="info")]
ui.kpi_cards(kpi)

st.write("")
ui.section("Start a check-up", "Choose how you want to be assessed", "play_circle")
tiles = [("stethoscope", "Symptom Checker", "Describe how you feel in your own words.", "views/symptoms.py", "linear-gradient(135deg,#0d9488,#14b8a6)"),
         ("water_drop", "Diabetes Risk", "Glucose, BMI, blood pressure and more.", "views/diabetes.py", "linear-gradient(135deg,#f59e0b,#f97316)"),
         ("cardiology", "Heart Risk", "Vitals, ECG and exercise-test results.", "views/heart.py", "linear-gradient(135deg,#ef4444,#f43f5e)"),
         ("gastroenterology", "Liver Risk", "Bilirubin, enzymes and proteins.", "views/liver.py", "linear-gradient(135deg,#8b5cf6,#6366f1)")]
cols = st.columns(4, gap="medium")
for col, (ic, title, text, page, grad) in zip(cols, tiles):
    with col:
        ui.tile(ic, title, text, grad)
        st.page_link(page, label="Open", icon=":material/arrow_forward:", width="stretch")

st.write("")
left, right = st.columns([1.35, 1], gap="large")
with left:
    ui.section("Latest risk by condition", "Most recent structured assessment", "speed", "violet")
    risk_df = df[df["kind"] == "risk"] if not df.empty and "kind" in df else pd.DataFrame()
    if risk_df.empty:
        ui.callout("brand", "No risk assessments yet", "Run the diabetes, heart or liver assessment to see your gauges here.")
    else:
        latest = risk_df.sort_values("created_at").groupby("disease").tail(1)
        gcols = st.columns(max(len(latest), 1))
        for c, r in zip(gcols, latest.itertuples()):
            with c, st.container(border=True):
                ui.show(ui.mini_gauge(round(r.risk_score, 1), r.disease, ui.RISK_COLORS.get(r.risk_level, "#64748b")), key=f"dash_g_{r.pred_id}")
        if len(risk_df) > 1:
            risk_df = risk_df.assign(created_at=to_local(risk_df["created_at"]))
            with st.container(border=True):
                ui.show(ui.trend_chart(risk_df, height=260), key="dash_trend")
with right:
    ui.section("Recent activity", "", "history", "brand")
    if df.empty:
        ui.callout("info", "Nothing here yet", "Your saved assessments will be listed here.")
    else:
        rows = ""
        for r in df.head(6).itertuples():
            tone = {"LOW": "good", "MEDIUM": "warn", "HIGH": "alert"}.get(r.risk_level, "info")
            ic = "stethoscope" if getattr(r, "kind", "risk") == "symptom" else "analytics"
            rows += (f"<div class='mp-row'><div style='display:flex;gap:.7rem;align-items:center;min-width:0'>"
                     f"<div style='width:36px;height:36px;border-radius:11px;background:{ui.soft(tone)};display:flex;align-items:center;justify-content:center;flex:none'>{ui.icon(ic, 20, ui.TONES[tone][0])}</div>"
                     f"<div style='min-width:0'><div style='font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{r.disease}</div>"
                     f"<div class='mp-muted' style='font-size:.76rem'>{ago(r.created_at)}</div></div></div>"
                     f"{ui.pill_html(f'{r.risk_score:.0f}%', tone)}</div>")
        st.markdown(ui.html(f"<div class='mp-card' style='padding:.6rem 1.1rem'>{rows}</div>"), unsafe_allow_html=True)
        st.page_link("views/history.py", label="View full history", icon=":material/history:")

st.write("")
tips = ["Walking briskly for 30 minutes most days lowers the risk of heart disease and type-2 diabetes.",
        "Regular check-ups catch silent conditions such as high blood pressure and high cholesterol early.",
        "Limiting alcohol and sugary drinks is one of the simplest ways to protect your liver.",
        "Sleeping 7 – 9 hours a night supports blood-sugar control and heart health.",
        "Know your numbers: blood pressure, fasting glucose and cholesterol are worth tracking yearly."]
ui.callout("violet", "Health tip of the day", tips[datetime.now().toordinal() % len(tips)], "lightbulb")
st.write("")
ui.disclaimer()
