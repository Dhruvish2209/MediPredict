import json

import streamlit as st

from app.utils import auth, db, ui
from app.utils.session import logout, refresh_user, require_login

user = require_login()
ui.page_header("Profile & Privacy", "Manage your details, who can see your results, and your data.", "manage_accounts")
st.write("")

left, right = st.columns(2, gap="large")
with left:
    ui.section("Account details", "Used to pre-fill assessment forms", "badge")
    with st.form("profile_form"):
        name = st.text_input("Full name", user["name"])
        st.text_input("Email", user["email"], disabled=True)
        c1, c2 = st.columns(2)
        age = c1.number_input("Age", 0, 110, int(user.get("age") or 0), help="0 = not set")
        opts = ["—", "Male", "Female"]
        sex = c2.selectbox("Sex", opts, index=opts.index(user["sex"]) if user.get("sex") in opts else 0)
        share = st.toggle("Share my results with doctors", value=bool(user.get("share_with_doctors", 1)),
                          help="When off, doctors cannot see any of your results in the Doctor Panel.")
        if st.form_submit_button("Save changes", type="primary", icon=":material/save:", width="stretch"):
            if not name.strip():
                st.error("Name cannot be empty.")
            else:
                db.update_user(user["user_id"], name=name.strip(), age=int(age) or None,
                               sex=None if sex == "—" else sex, share_with_doctors=int(share))
                refresh_user()
                st.session_state.pop("_forms", None)  # let forms re-pick the new age/sex
                st.toast("Profile updated", icon="✅")
                st.rerun()
with right:
    ui.section("Change password", "", "key", "violet")
    with st.form("pw_form", clear_on_submit=True):
        cur = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password", help="At least 8 characters with a letter and a number.")
        if st.form_submit_button("Update password", icon=":material/lock_reset:", width="stretch"):
            err = auth.change_password(user["user_id"], cur, new)
            st.error(err) if err else st.success("Password updated.")

st.write("")
ui.section("Your data", "You are in control", "shield_person", "info")
c1, c2 = st.columns(2, gap="large")
with c1, st.container(border=True):
    st.markdown("**Download everything**")
    st.caption("A JSON file with your profile and every saved result.")
    data = {"profile": {k: user.get(k) for k in ("name", "email", "role", "age", "sex")},
            "results": db.get_user_history(user["user_id"])}
    st.download_button("Download my data (JSON)", json.dumps(data, indent=2, default=str), "medipredict_my_data.json",
                       "application/json", icon=":material/download:", width="stretch")
with c2, st.container(border=True):
    st.markdown("**Clear history**")
    st.caption("Permanently deletes all of your saved results.")
    if st.checkbox("I understand this can't be undone", key="clr_ok"):
        if st.button("Delete all my results", icon=":material/delete_sweep:", width="stretch"):
            db.clear_user_history(user["user_id"])
            st.toast("History cleared", icon="🗑️")

with st.expander("Delete my account", icon=":material/warning:"):
    st.warning("This removes your account and all your results permanently.")
    confirm = st.text_input("Type your email to confirm")
    if st.button("Delete account", type="primary", disabled=confirm.strip().lower() != user["email"].lower()):
        db.delete_user(user["user_id"])
        logout()
        st.rerun()
