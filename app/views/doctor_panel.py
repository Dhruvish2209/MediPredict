import pandas as pd
import streamlit as st

from app.utils import db, ui
from app.utils.session import require_doctor
from app.utils.timefmt import ago, to_local
from app.views.detail import render_detail

doctor = require_doctor()
ui.page_header("Doctor Panel", "Review patient results, triage high-risk cases and leave clinical notes.", "clinical_notes",
               chips=["Only patients who opted in are shown"])
st.write("")

recs = db.get_all_predictions(limit=2000)
stats = db.get_stats()
df = pd.DataFrame(recs)
if df.empty:
    ui.kpi_cards([dict(label="Patients", value=stats["patients"], sub="Registered", icon="groups", tone="brand")])
    st.write("")
    ui.callout("info", "No shared results yet", "Patient results appear here once they have run an assessment and allow sharing.")
    st.stop()
df["when"] = to_local(df["created_at"])
high = df[df["risk_level"] == "HIGH"]
ui.kpi_cards([
    dict(label="Patients", value=df["user_id"].nunique(), sub=f"{stats['patients']} registered", icon="groups", tone="brand"),
    dict(label="Results", value=len(df), sub="Shared with doctors", icon="assignment", tone="violet"),
    dict(label="High-risk", value=len(high), sub="Need attention", icon="warning", tone="alert"),
    dict(label="Last 7 days", value=int((df["when"] > pd.Timestamp.now() - pd.Timedelta(days=7)).sum()), sub="New results", icon="trending_up", tone="info")])
st.write("")


def record_card(r, key):
    patient = {"name": r["name"], "age": r.get("age"), "sex": r.get("sex")}
    tone = {"LOW": "good", "MEDIUM": "warn", "HIGH": "alert"}[r["risk_level"]]
    title = f"{r['name']} · {r['disease']} · {r['risk_score']:.0f}% · {ago(r['created_at'])}"
    with st.expander(title, icon=":material/warning:" if tone == "alert" else ":material/assignment:"):
        for n in db.get_notes(r["pred_id"]):
            ui.callout("info", f"{n['doctor_name']} · {ago(n['created_at'])}", n["note"], "clinical_notes")
        with st.form(f"note_{key}_{r['pred_id']}", border=False):
            note = st.text_area("Add a clinical note (visible to the patient)", key=f"nt_{key}_{r['pred_id']}", height=80)
            if st.form_submit_button("Save note", icon=":material/save:"):
                if note.strip():
                    db.add_note(r["pred_id"], doctor["user_id"], note)
                    st.toast("Note saved", icon="✅")
                    st.rerun()
        render_detail(r, doctor, patient, f"dp_{key}")


t1, t2, t3, t4 = st.tabs(["Triage queue", "Patients", "Analytics", "All records"])

with t1:
    ui.section("High-risk results", "Newest first", "priority_high", "alert")
    if high.empty:
        ui.callout("good", "No high-risk results", "Nothing needs urgent attention right now.")
    for r in high.head(15).to_dict("records"):
        record_card(r, "q")

with t2:
    agg = df.groupby(["user_id", "name", "email"]).agg(results=("pred_id", "count"), high=("risk_level", lambda s: (s == "HIGH").sum()),
                                                        last=("when", "max"), peak=("risk_score", "max")).reset_index().sort_values("last", ascending=False)
    st.dataframe(agg[["name", "email", "results", "high", "peak", "last"]].rename(columns={"name": "Patient", "email": "Email", "results": "Results", "high": "High-risk", "peak": "Peak %", "last": "Last activity"}),
                 hide_index=True, width="stretch",
                 column_config={"Peak %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
                                "Last activity": st.column_config.DatetimeColumn(format="DD MMM YYYY, HH:mm")})
    pick = st.selectbox("Open a patient", agg["user_id"], format_func=lambda i: agg.set_index("user_id").loc[i, "name"])
    pdf = df[df["user_id"] == pick]
    rk = pdf[pdf["kind"] == "risk"]
    if len(rk) >= 2:
        with st.container(border=True):
            ui.show(ui.trend_chart(rk.assign(created_at=rk["when"])), key="dp_trend")
    for r in pdf.head(20).to_dict("records"):
        record_card(r, "p")

with t3:
    a, b = st.columns(2, gap="large")
    with a:
        ui.section("Results by condition", "", "pie_chart")
        vc = df["disease"].value_counts().head(8)
        with st.container(border=True):
            ui.show(ui.donut(list(vc.index), list(vc.values), center_text=str(len(df))), key="an_donut")
    with b:
        ui.section("Risk levels", "", "bar_chart", "violet")
        lv = df["risk_level"].value_counts().reindex(["LOW", "MEDIUM", "HIGH"]).fillna(0)
        with st.container(border=True):
            ui.show(ui.donut(["Low", "Moderate", "High"], list(lv.values), [ui.RISK_COLORS[k] for k in ["LOW", "MEDIUM", "HIGH"]]), key="an_levels")
    ui.section("Activity over time", "", "timeline", "info")
    daily = df.assign(day=df["when"].dt.date).groupby("day").size().reset_index(name="results")
    with st.container(border=True):
        st.bar_chart(daily, x="day", y="results", color="#0d9488", height=240)

with t4:
    lv = st.multiselect("Filter by level", ["LOW", "MEDIUM", "HIGH"], default=["LOW", "MEDIUM", "HIGH"])
    f = df[df["risk_level"].isin(lv)][["when", "name", "email", "disease", "risk_score", "risk_level"]]
    st.dataframe(f, hide_index=True, width="stretch", column_config={
        "when": st.column_config.DatetimeColumn("Date", format="DD MMM YYYY, HH:mm"),
        "risk_score": st.column_config.ProgressColumn("Score %", min_value=0, max_value=100, format="%.0f%%")})
    st.download_button("Export CSV", f.to_csv(index=False).encode(), "medipredict_records.csv", "text/csv", icon=":material/download:")
