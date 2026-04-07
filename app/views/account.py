from __future__ import annotations

import streamlit as st

from app.utils.api_client import APIClient, APIClientError
from app.utils.session import logout


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

    st.subheader("", divider="red")
    st.subheader("Danger Zone")

    if st.button("Delete My Account", type="primary"):
        try:
            email_to_delete = st.session_state.get("user_email")
            if email_to_delete:
                api.delete_user(email=email_to_delete)
                st.success("Account deleted successfully.")
                logout()
                st.rerun()
            else:
                st.error("Could not determine user email to delete.")
        except APIClientError as exc:
            st.error(f"Failed to delete account: {exc}")
