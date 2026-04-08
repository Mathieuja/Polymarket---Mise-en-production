from __future__ import annotations

import streamlit as st

from app.frontend.utils.api_client import APIClient
from app.frontend.utils.session import logout


def render(api: APIClient) -> None:
    st.header("Account")

    st.write(
        {
            "email": st.session_state.get("user_email"),
            "authenticated": st.session_state.get("is_authenticated"),
        }
    )

    if st.button("Logout"):
        logout()
        st.rerun()
