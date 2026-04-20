from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path.cwd()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st  # noqa: E402

from config import get_settings  # noqa: E402
from utils.api_client import APIClient  # noqa: E402
from utils.session import init_session_state  # noqa: E402
from utils.styles import apply_base_styles  # noqa: E402
from utils.ui import badge_html  # noqa: E402
from views import account, history, login, metrics, portfolio, trading  # noqa: E402


PAGES = {
    "Login": login,
    "Trading": trading,
    "Portfolio": portfolio,
    "History": history,
    "Metrics": metrics,
    "Account": account,
}


def _render_sidebar() -> str:
    settings = get_settings()
    is_authenticated = bool(st.session_state.get("is_authenticated"))
    user_email = st.session_state.get("user_email") or "Guest session"

    st.sidebar.markdown(
        """
        <section class="sidebar-brand">
          <div class="sidebar-brand__eyebrow">Polymarket Demo</div>
          <h2>Paper Trading Lab</h2>
          <p>Explore prediction markets with a clean, guided interface built for product demos.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    pages = ["Login"]
    if is_authenticated:
        pages = ["Trading", "Portfolio", "History", "Metrics", "Account"]

    current = st.session_state.get("nav_page")
    if current not in pages:
        current = pages[0]

    st.sidebar.caption("Navigate")
    selected = st.sidebar.radio(
        "Page",
        options=pages,
        index=pages.index(current),
        label_visibility="collapsed",
    )
    st.session_state.nav_page = selected

    auth_badge = (
        badge_html("Signed in", "success")
        if is_authenticated
        else badge_html("Preview", "warning")
    )
    st.sidebar.markdown(
        f"""
        <section class="sidebar-panel">
          <strong>{user_email}</strong>
          <p style="margin-top:0.4rem;">{auth_badge}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        f"""
        <section class="sidebar-panel">
          <p><strong>Environment</strong></p>
          <p style="margin-top:0.5rem;">{badge_html(settings.backend_mode, "brand")}</p>
          <p style="margin-top:0.55rem; font-size:0.85rem;">API base</p>
          <p style="font-size:0.78rem; color:#d8e7ef;">{settings.api_url}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        """
        <section class="sidebar-panel">
          <p><strong>Demo focus</strong></p>
          <p style="margin-top:0.45rem;">
            Read the market, place paper trades, and follow how portfolio value evolves over time.
          </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    return selected


def main() -> None:
    settings = get_settings()

    st.set_page_config(page_title=settings.app_name, layout="wide")
    apply_base_styles()

    init_session_state()

    api = APIClient(backend_mode=settings.backend_mode, api_url=settings.api_url)

    nav_override = st.session_state.get("nav_override")
    if nav_override:
        st.session_state.nav_page = nav_override
        st.session_state.nav_override = None
        st.session_state.nav_key = int(st.session_state.get("nav_key", 0)) + 1
        st.rerun()

    if not st.session_state.get("is_authenticated"):
        st.session_state.nav_page = "Login"

    page_name = _render_sidebar()
    module = PAGES[page_name]
    module.render(api)


if __name__ == "__main__":
    main()
