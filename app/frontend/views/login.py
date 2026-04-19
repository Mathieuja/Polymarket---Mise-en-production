from __future__ import annotations

import streamlit as st
from utils.api_client import APIClient, APIClientError
from utils.ui import render_page_header


def render(api: APIClient) -> None:
    render_page_header(
        "Prediction markets, made approachable.",
        (
            "Sign in to explore a polished paper-trading demo: read "
            "probabilities, build a portfolio, and follow your positions "
            "without the friction of a full trading stack."
        ),
        eyebrow="Welcome",
        badge_label="Guided demo",
        badge_tone="brand",
    )

    if st.session_state.get("is_authenticated"):
        st.markdown(
            f"""
            <section class="hero-panel">
              <div class="hero-panel__eyebrow">Session ready</div>
              <h2>Welcome back</h2>
              <p>
                You are signed in as {st.session_state.get('user_email')}. Use the
                navigation on the left to move from market discovery to portfolio tracking.
              </p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        return

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown(
            """
            <section class="hero-panel">
              <div class="hero-panel__eyebrow">Why this app</div>
              <h2>Learn the shape of a market before you trade it.</h2>
              <p>
                This interface is built for a curious audience: simple enough for a
                first encounter with prediction markets, structured enough to feel like
                a real product demo.
              </p>
              <div class="hero-panel__list">
                <div class="hero-panel__item">
                  <strong>Read probabilities quickly</strong>
                  <p>Each market surfaces YES and NO pricing as a simple probability split.</p>
                </div>
                <div class="hero-panel__item">
                  <strong>Build conviction with paper trades</strong>
                  <p>
                    Place simulated BUY and SELL orders before worrying about
                    execution complexity.
                  </p>
                </div>
                <div class="hero-panel__item">
                  <strong>Track outcomes through portfolio metrics</strong>
                  <p>Follow cash, exposure, value, and PnL in a single visual flow.</p>
                </div>
              </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="feature-grid">
              <div class="feature-card">
                <h4>Discovery</h4>
                <p>
                  Scan live-looking market snapshots and focus on the latest
                  probability signal.
                </p>
              </div>
              <div class="feature-card">
                <h4>Simulation</h4>
                <p>
                  Experiment with position sizing and outcome selection using a
                  low-friction ticket.
                </p>
              </div>
              <div class="feature-card">
                <h4>Teaching value</h4>
                <p>
                  Every screen includes short hints so non-specialists can
                  understand the mechanics fast.
                </p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        with st.form("login_form"):
            st.markdown(
                """
                <div class="section-header">
                  <div>
                    <h3>Sign in to the demo</h3>
                    <p>Use the demo account configured for the current environment.</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            email = st.text_input("Email", placeholder="demo@example.com")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Enter paper trading workspace", type="primary")

        st.caption(
            "This login flow is intentionally lightweight and designed for "
            "product demonstration."
        )

    if submitted:
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
