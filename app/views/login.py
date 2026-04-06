from __future__ import annotations

import streamlit as st

from app.utils.api_client import APIClient, APIClientError


def render(api: APIClient) -> None:
    st.header("Login")

    if st.session_state.get("is_authenticated"):
        st.success(f"Logged in as {st.session_state.get('user_email')}")
        st.info("Use the sidebar to navigate.")
        return

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign in", type="primary"):
        try:
            data = api.login(email=email, password=password)
        except APIClientError as exc:
            st.error(str(exc))
            return

        st.session_state.is_authenticated = True
        st.session_state.token = data.get("access_token")
        st.session_state.user_email = data.get("email", email)
        st.session_state.nav_page = "Trading"
        st.rerun()
