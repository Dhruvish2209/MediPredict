import pandas as pd
import streamlit as st

from app.utils import db, ui
from app.utils.session import require_login
from app.utils.timefmt import to_local
from app.views.detail import render_detail

user = require_login()
ui.page_header("Your History", "Every symptom check and risk assessment you've run, with full explanations.", "history")
st.write("")

hist = db.get_user_history(user["user_id"])
if not hist:
    ui.callout("brand", "No saved results yet", "Run a symptom check or a risk assessment and it will show up here.")
    st.page_link("views/symptoms.py", label="Start with the Symptom Checker", icon=":material/stethoscope:")
    st.stop()

df = pd.DataFrame(hist)
df["when"] = to_local(df["created_at"])
df["type"] = df["kind"].map({"symptom": "Symptom check", "risk": "Risk assessment"}).fillna("Risk assessment")

c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
kinds = c1.multiselect("Type", sorted(df["type"].unique()), default=sorted(df["type"].unique()))
levels = c2.multiselect("Level", ["LOW", "MEDIUM", "HIGH"], default=["LOW", "MEDIUM", "HIGH"])
q = c3.text_input("Search", placeholder="e.g. Heart, Dengue…")
f = df[df["type"].isin(kinds) & df["risk_level"].isin(levels)]
if q:
    f = f[f["disease"].str.contains(q, case=False, na=False)]

ui.kpi_cards([
    dict(label="Results", value=len(f), sub=f"of {len(df)} saved", icon="assignment", tone="brand"),
    dict(label="High level", value=int((f["risk_level"] == "HIGH").sum()), sub="Flagged", icon="warning", tone="alert"),
    dict(label="Conditions", value=f["disease"].nunique(), sub="Distinct", icon="category", tone="violet"),
    dict(label="Latest", value=f["when"].max().strftime("%d %b") if len(f) else "–", sub="Most recent", icon="event", tone="info")])

rk = f[f["kind"] == "risk"]
if len(rk) >= 2:
    st.write("")
    ui.section("Risk trend", "Your structured assessments over time", "show_chart", "violet")
    with st.container(border=True):
        ui.show(ui.trend_chart(rk.assign(created_at=rk["when"])), key="hist_trend")

st.write("")
ui.section("All results", "Select a row to open the full explanation", "table_rows")
view = f[["pred_id", "when", "type", "disease", "risk_score", "risk_level"]].rename(
    columns={"when": "Date", "type": "Type", "disease": "Result", "risk_score": "Score %", "risk_level": "Level"})
event = st.dataframe(view.drop(columns="pred_id"), hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                     column_config={"Date": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm"),
                                    "Score %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%")})
st.download_button("Export CSV", f[["when", "type", "disease", "risk_score", "risk_level"]].to_csv(index=False).encode(),
                   "medipredict_history.csv", "text/csv", icon=":material/download:")

rows = event.selection.rows if event and event.selection else []
if rows:
    rec_id = int(view.iloc[rows[0]]["pred_id"])
    rec = db.get_prediction(rec_id)
    st.divider()
    h1, h2 = st.columns([4, 1])
    h1.markdown(f"### {rec['disease']}  \n<span class='mp-muted'>{view.iloc[rows[0]]['Date']:%d %b %Y, %H:%M}</span>", unsafe_allow_html=True)
    with h2:
        if st.button("Delete", icon=":material/delete:", width="stretch", key="del_open"):
            st.session_state["confirm_del"] = rec_id
    if st.session_state.get("confirm_del") == rec_id:
        ui.callout("warn", "Delete this result?", "This cannot be undone.")
        a, b = st.columns(2)
        if a.button("Yes, delete", type="primary", key="del_yes"):
            db.delete_prediction(rec_id, user["user_id"])
            st.session_state.pop("confirm_del", None)
            st.rerun()
        if b.button("Cancel", key="del_no"):
            st.session_state.pop("confirm_del", None)
            st.rerun()
    notes = db.get_notes(rec_id)
    for n in notes:
        ui.callout("info", f"Note from {n['doctor_name']}", n["note"], "clinical_notes")
    render_detail(rec, user, user, "hist")
