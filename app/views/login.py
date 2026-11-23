import streamlit as st

from app.utils import auth, db, ui
from app.utils.session import login_user

left, right = st.columns([1.1, 1], gap="large")

with left:
    st.markdown(ui.html(f"""
    <div class='mp-auth-hero'>
      <div style='display:flex;align-items:center;gap:.7rem;position:relative;z-index:1'>
        <div style='width:46px;height:46px;border-radius:14px;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center'>{ui.icon('monitor_heart', 28, '#fff')}</div>
        <b style='font-family:Plus Jakarta Sans,sans-serif;font-size:1.4rem'>MediPredict</b>
      </div>
      <h1>Understand your health risk, not just a number.</h1>
      <p>Describe symptoms in plain words or enter lab values. Get an AI estimate together with a clear explanation of what drove it.</p>
      <div class='hide-sm'>
        <div class='mp-feature'><div class='ic'>{ui.icon('chat', 22, '#fff')}</div><div><b>Talk to it in plain language</b><span class='d'>NLP understands "fever for 3 days, no cough".</span></div></div>
        <div class='mp-feature'><div class='ic'>{ui.icon('insights', 22, '#fff')}</div><div><b>Explainable by design</b><span class='d'>SHAP shows exactly which factors moved your risk.</span></div></div>
        <div class='mp-feature'><div class='ic'>{ui.icon('tune', 22, '#fff')}</div><div><b>What-if simulator</b><span class='d'>See how lowering glucose or BP changes the estimate.</span></div></div>
        <div class='mp-feature'><div class='ic'>{ui.icon('picture_as_pdf', 22, '#fff')}</div><div><b>Shareable PDF reports</b><span class='d'>Take your results to your doctor.</span></div></div>
        <div class='mp-stats'><div><b>41</b><span>Conditions</span></div><div><b>3</b><span>Risk models</span></div><div><b>131</b><span>Symptoms</span></div></div>
      </div>
    </div>"""), unsafe_allow_html=True)

with right:
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    tab_in, tab_up = st.tabs(["Sign in", "Create account"])

    with tab_in:
        st.markdown("<h2 style='margin:.4rem 0 0'>Welcome back</h2><p class='mp-muted'>Sign in to continue to your dashboard.</p>", unsafe_allow_html=True)
        with st.form("login_form", border=False):
            email = st.text_input("Email", placeholder="you@example.com", autocomplete="email")
            password = st.text_input("Password", type="password", placeholder="Your password")
            ok = st.form_submit_button("Sign in", type="primary", width="stretch")
        if ok:
            user, err = auth.login(email, password)
            if user:
                login_user(user)
                st.rerun()
            else:
                st.error(err)

    with tab_up:
        st.markdown("<h2 style='margin:.4rem 0 0'>Create your account</h2><p class='mp-muted'>Free, private, and takes under a minute.</p>", unsafe_allow_html=True)
        with st.form("register_form", border=False):
            name = st.text_input("Full name", placeholder="Jane Doe")
            email_r = st.text_input("Email", key="reg_email", placeholder="you@example.com")
            c1, c2 = st.columns(2)
            pw = c1.text_input("Password", type="password", key="reg_pw", help="At least 8 characters with a letter and a number.")
            pw2 = c2.text_input("Confirm password", type="password", key="reg_pw2")
            c3, c4, c5 = st.columns([1, 1, 1])
            role_label = c3.selectbox("I am a", ["Patient", "Doctor"])
            age = c4.number_input("Age (optional)", 0, 110, 0, help="Used to pre-fill assessment forms. 0 = skip.")
            sex = c5.selectbox("Sex (optional)", ["—", "Male", "Female"])
            code = st.text_input("Doctor invitation code", type="password", help="Only needed when registering as a doctor.")
            go = st.form_submit_button("Create account", type="primary", width="stretch")
        if go:
            if pw != pw2:
                st.error("Passwords do not match.")
            else:
                uid, err = auth.register(name, email_r, pw, "doctor" if role_label == "Doctor" else "patient", code,
                                         int(age) or None, None if sex == "—" else sex)
                if err:
                    st.error(err)
                else:
                    login_user(db.get_user(uid))
                    st.rerun()
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    ui.disclaimer()
