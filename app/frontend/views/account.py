from __future__ import annotations

import streamlit as st
from utils.api_client import APIClient
from utils.session import logout
from utils.ui import (
    badge_html,
    render_info_card,
    render_label_value_pairs,
    render_page_header,
    render_section_header,
)


def render(api: APIClient) -> None:
    is_authenticated = bool(st.session_state.get("is_authenticated"))
    selected_portfolio_id = str(st.session_state.get("selected_portfolio_id") or "-")
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
          <h2>{st.session_state.get('user_email') or 'Guest session'}</h2>
          <p>{auth_label}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            f"""
            <section class="spotlight-card">
              <div class="spotlight-card__label">Session status</div>
              <div class="spotlight-card__value">
                {'Ready to trade' if is_authenticated else 'Preview only'}
              </div>
              <div class="spotlight-card__body">
                This state controls whether the app behaves like a signed-in paper trading
                workspace or a simple pre-login showcase.
              </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""
            <section class="spotlight-card">
              <div class="spotlight-card__label">Selected portfolio</div>
              <div class="spotlight-card__value">{selected_portfolio_id}</div>
              <div class="spotlight-card__body">
                Portfolio context is shared across trading, metrics, and history
                to keep the demo flow coherent.
              </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    render_label_value_pairs(
        [
            ("Email", str(st.session_state.get("user_email") or "-")),
            ("Authenticated", "Yes" if is_authenticated else "No"),
            ("Selected portfolio", selected_portfolio_id),
        ]
    )

    render_info_card(
        "Why this page exists",
        (
            "In a fuller product, this area would include permissions, "
            "credentials, and profile preferences. For the demo, it keeps "
            "the session explicit and easy to reset."
        ),
        tone="brand",
    )

    if st.button("Logout"):
        logout()
        st.rerun()
