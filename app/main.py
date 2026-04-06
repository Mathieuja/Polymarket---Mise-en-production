from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path so we can import `app.*` when running:
#   streamlit run app/main.py
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.utils.api_client import APIClient  # noqa: E402
from app.utils.session import init_session_state  # noqa: E402
from app.utils.styles import apply_base_styles  # noqa: E402
from app.views import account, history, login, metrics, portfolio, trading  # noqa: E402


PAGES = {
    "Login": login,
    "Trading": trading,
    "Portfolio": portfolio,
    "History": history,
    "Metrics": metrics,
    "Account": account,
}


def _render_sidebar() -> str:
    st.sidebar.title("Navigation")

    is_authenticated = bool(st.session_state.get("is_authenticated"))
    pages = ["Login"]
    if is_authenticated:
        pages = ["Trading", "Portfolio", "History", "Metrics", "Account"]

    current = st.session_state.get("nav_page")
    if current not in pages:
        current = pages[0]

    selected = st.sidebar.radio("Page", options=pages, index=pages.index(current))
    st.session_state.nav_page = selected

    st.sidebar.caption("Backend")
    st.sidebar.code(f"BACKEND_MODE={get_settings().backend_mode}\nAPI_URL={get_settings().api_url}")

    return selected


def main() -> None:
    settings = get_settings()

    st.set_page_config(page_title=settings.app_name, layout="wide")
    apply_base_styles()

    init_session_state()

    api = APIClient(backend_mode=settings.backend_mode, api_url=settings.api_url)

    page_name = _render_sidebar()
    module = PAGES[page_name]
    module.render(api)


if __name__ == "__main__":
    main()
