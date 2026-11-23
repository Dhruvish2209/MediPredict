"""MediPredict entry point.   Run from the project root:   streamlit run app/main.py"""
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:          # makes `import app.utils...` work however Streamlit is launched
    sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=UserWarning)

import streamlit as st  # noqa: E402

st.set_page_config(page_title="MediPredict · Explainable health screening", page_icon="🩺", layout="wide",
                   initial_sidebar_state="auto")

from app.utils import db, ui  # noqa: E402
from app.utils.config import ASSETS_DIR  # noqa: E402
from app.utils.session import current_user, logout  # noqa: E402

db.init_db()
user = current_user()
st.session_state["_hide_sidebar"] = user is None
ui.inject_css()

if user is None:
    pg = st.navigation([st.Page("views/login.py", title="Sign in", icon=":material/login:", url_path="login")],
                       position="hidden")
else:
    st.logo(str(ASSETS_DIR / "logo.svg"), icon_image=str(ASSETS_DIR / "icon.svg"), size="large")
    nav = {
        "Overview": [st.Page("views/dashboard.py", title="Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True)],
        "Check-up": [
            st.Page("views/symptoms.py", title="Symptom Checker", icon=":material/stethoscope:", url_path="symptoms"),
            st.Page("views/diabetes.py", title="Diabetes Risk", icon=":material/water_drop:", url_path="diabetes"),
            st.Page("views/heart.py", title="Heart Risk", icon=":material/cardiology:", url_path="heart"),
            st.Page("views/liver.py", title="Liver Risk", icon=":material/gastroenterology:", url_path="liver"),
        ],
        "My health": [
            st.Page("views/history.py", title="History", icon=":material/history:", url_path="history"),
            st.Page("views/profile.py", title="Profile & Privacy", icon=":material/manage_accounts:", url_path="profile"),
        ],
    }
    if user["role"] == "doctor":
        nav["Clinic"] = [st.Page("views/doctor_panel.py", title="Doctor Panel", icon=":material/clinical_notes:", url_path="doctor")]
    nav["Learn"] = [st.Page("views/insights.py", title="Model Insights", icon=":material/science:", url_path="insights")]
    pg = st.navigation(nav, position="sidebar")

    with st.sidebar:
        initial = (user["name"] or "?")[:1].upper()
        role = "Doctor" if user["role"] == "doctor" else "Patient"
        st.markdown(ui.html(f"""<div class='mp-user'><div class='mp-avatar'>{initial}</div>
            <div style='min-width:0'><div style='font-weight:700;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{user['name']}</div>
            <div style='font-size:.74rem;color:#8fb0d6'>{role}</div></div></div>"""), unsafe_allow_html=True)
        if st.button("Sign out", icon=":material/logout:", width="stretch"):
            logout()
            st.rerun()

pg.run()
