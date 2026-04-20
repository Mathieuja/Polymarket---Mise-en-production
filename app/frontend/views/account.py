from __future__ import annotations

import streamlit as st
from utils.api_client import APIClient, APIClientError
from utils.session import logout
from utils.ui import (
    badge_html,
    render_api_error_state,
    render_info_card,
    render_label_value_pairs,
    render_page_header,
    render_section_header,
)


def render(api: APIClient) -> None:
    is_authenticated = bool(st.session_state.get("is_authenticated"))
    selected_portfolio_id = str(st.session_state.get("selected_portfolio_id") or "-")
    token = st.session_state.get("token")

    user_data: dict | None = None
    if is_authenticated:
        try:
            user_data = api.get_me(token=token)
            st.session_state.user = user_data
            st.session_state.user_email = user_data.get("email", st.session_state.get("user_email"))
        except APIClientError:
            user_data = st.session_state.get("user")

    email = (user_data or {}).get("email") or st.session_state.get("user_email") or "Guest session"

    render_page_header(
        "Account and session",
        (
            "A polished session view for the current demo: identity, current "
            "workspace context, and a clean way to reset the experience."
        ),
        eyebrow="Account",
        badge_label="Session control",
        badge_tone="brand",
    )

    render_section_header(
        "Current session",
        (
            "This project keeps authentication intentionally lightweight so the "
            "focus stays on the product experience."
        ),
    )
    auth_label = (
        badge_html("authenticated", "success")
        if is_authenticated
        else badge_html("not signed in", "warning")
    )
    st.markdown(
        f"""
        <section class="hero-panel">
          <div class="hero-panel__eyebrow">Identity</div>
          <h2>{email}</h2>
          <p>{auth_label}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    tab_profile, tab_security = st.tabs(["Profile", "Security"])

    with tab_profile:
        render_section_header(
            "Profile information",
            "Identity and workspace context used by trading, metrics, and history views.",
        )

        if is_authenticated and user_data is None:
            render_api_error_state(
                APIClientError("Unable to load user profile"),
                resource="current user profile",
            )

        render_label_value_pairs(
            [
                ("Email", str(email)),
                ("Authenticated", "Yes" if is_authenticated else "No"),
                ("Selected portfolio", selected_portfolio_id),
                ("User ID", str((user_data or {}).get("id", "-"))),
            ]
        )

        render_info_card(
            "Profile notes",
            (
                "This page preserves the legacy account flow while using the new app layout. "
                "Profile details are fetched from the backend when available."
            ),
            tone="brand",
        )

        if st.button("Log out", key="account_logout"):
            logout()
            st.rerun()

    with tab_security:
        render_section_header(
            "Change password",
            "Update account password through backend validation.",
        )

        with st.form("account_change_password_form"):
            current_password = st.text_input("Current password", type="password")
            new_password = st.text_input("New password", type="password")
            new_password_confirm = st.text_input("Confirm new password", type="password")
            submitted = st.form_submit_button("Change password", type="primary")

        if submitted:
            if not current_password:
                st.error("Please enter your current password")
                return
            if not new_password:
                st.error("Please enter a new password")
                return
            if len(new_password) < 8:
                st.error("The new password must be at least 8 characters long")
                return
            if new_password != new_password_confirm:
                st.error("The new passwords do not match")
                return
            if current_password == new_password:
                st.error("The new password must be different from the old one")
                return

            try:
                api.change_password(
                    token=token,
                    current_password=current_password,
                    new_password=new_password,
                    new_password_confirm=new_password_confirm,
                )
            except APIClientError as exc:
                st.error(str(exc))
                return

            st.success("Password changed successfully. Please log in again.")
            logout()
            st.rerun()
