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

    if "login_email_input" not in st.session_state:
        st.session_state.login_email_input = ""
    if "prefill_login_email" in st.session_state:
      st.session_state.login_email_input = st.session_state.pop("prefill_login_email")
    if "auth_notice" in st.session_state:
        st.success(st.session_state.pop("auth_notice"))

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
        tab_signin, tab_signup = st.tabs(["Sign in", "Create account"])

        submitted_login = False
        login_email = ""
        login_password = ""
        submitted_signup = False
        signup_name = ""
        signup_email = ""
        signup_password = ""
        signup_confirm_password = ""

        with tab_signin:
            with st.form("login_form"):
                st.markdown(
                    """
                    <div class="section-header">
                      <div>
                        <h3>Sign in to your account</h3>
                        <p>Access your portfolio, history, and market workspace.</p>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                login_email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                    key="login_email_input",
                )
                login_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter password",
                    key="login_password_input",
                )
                submitted_login = st.form_submit_button(
                    "Enter paper trading workspace",
                    type="primary",
                )

        with tab_signup:
            with st.form("signup_form"):
                st.markdown(
                    """
                    <div class="section-header">
                      <div>
                        <h3>Create your account</h3>
                        <p>Set up a secure account to use API mode authentication.</p>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                signup_name = st.text_input(
                    "Full name",
                    placeholder="Jane Doe",
                    key="signup_name_input",
                )
                signup_email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                    key="signup_email_input",
                )
                signup_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="At least 8 characters",
                    key="signup_password_input",
                )
                signup_confirm_password = st.text_input(
                    "Confirm password",
                    type="password",
                    placeholder="Re-enter password",
                    key="signup_confirm_password_input",
                )
                submitted_signup = st.form_submit_button("Create account", type="primary")

        st.caption(
            "In API mode, account creation and sign-in are backed by the backend database."
        )

    if submitted_login:
        if not login_email.strip() or not login_password:
            st.error("Email and password are required")
            return

        try:
            data = api.login(email=login_email, password=login_password)
        except APIClientError as exc:
            st.error(str(exc))
            return

        st.session_state.is_authenticated = True
        st.session_state.token = data.get("access_token")
        st.session_state.user_email = data.get("email", login_email)
        try:
          user = api.get_me(token=st.session_state.token)
          st.session_state.user = user
          st.session_state.user_email = user.get("email", st.session_state.user_email)
        except APIClientError:
          st.session_state.user = None
        st.session_state.nav_page = "Trading"
        st.rerun()

    if submitted_signup:
        if not signup_name.strip() or not signup_email.strip() or not signup_password:
            st.error("Name, email, and password are required")
            return

        if signup_password != signup_confirm_password:
            st.error("Passwords do not match")
            return

        try:
            api.register(name=signup_name, email=signup_email, password=signup_password)
        except APIClientError as exc:
            st.error(str(exc))
            return

        st.session_state.is_authenticated = False
        st.session_state.token = None
        st.session_state.user_email = None
        st.session_state.prefill_login_email = signup_email.strip().lower()
        st.session_state.auth_notice = "Account created successfully. Please sign in."
        st.session_state.nav_page = "Login"
        st.rerun()
