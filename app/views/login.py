from __future__ import annotations

import streamlit as st

from app.utils.api_client import APIClient, APIClientError


def render(api: APIClient) -> None:
    st.header("Login / Sign Up")

    if st.session_state.get("is_authenticated"):
        st.success(f"Logged in as {st.session_state.get('user_email')}")
        st.info("Use the sidebar to navigate.")
        return

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        st.subheader("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Sign in", type="primary"):
            try:
                data = api.login(email=login_email, password=login_password)
                st.session_state.is_authenticated = True
                st.session_state.token = data.get("access_token")
                st.session_state.user_email = data.get("email", login_email)
                st.session_state.nav_page = "Trading"
                st.rerun()
            except APIClientError as exc:
                st.error(str(exc))

    with signup_tab:
        st.subheader("Create a new account")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        signup_password_confirm = st.text_input(
            "Confirm Password", type="password", key="signup_password_confirm"
        )

        if st.button("Create account"):
            if signup_password != signup_password_confirm:
                st.error("Passwords do not match")
            else:
                try:
                    api.create_user(email=signup_email, password=signup_password)
                    st.success("Account created successfully! You can now log in.")
                except APIClientError as exc:
                    st.error(str(exc))
