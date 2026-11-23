"""Thin wrapper around st.session_state for the signed-in user."""
import streamlit as st

from app.utils import db


def current_user():
    return st.session_state.get("user")


def login_user(user: dict):
    st.session_state["user"] = {k: user.get(k) for k in
                                ("user_id", "name", "email", "role", "age", "sex", "share_with_doctors", "last_login")}


def refresh_user():
    u = current_user()
    if u:
        fresh = db.get_user(u["user_id"])
        if fresh:
            login_user(fresh)


def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def require_login():
    """Call at the top of every page. Stops the script if nobody is signed in."""
    u = current_user()
    if not u:
        st.warning("Please sign in first.")
        st.stop()
    return u


def require_doctor():
    u = require_login()
    if u["role"] != "doctor":
        st.error("This area is only available to registered doctors.")
        st.stop()
    return u
