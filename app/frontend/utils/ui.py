from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

import pandas as pd
import streamlit as st

from utils.api_client import APIClientError


def format_currency(value: float) -> str:
    return f"${float(value):,.2f}"


def format_signed_currency(value: float) -> str:
    sign = "+" if float(value) > 0 else ""
    return f"{sign}{format_currency(value)}"


def format_probability(value: float) -> str:
    return f"{float(value) * 100:.0f}%"


def format_quantity(value: float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"


def format_timestamp(value: str | None) -> str:
    if not value:
        return "-"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def badge_html(label: str, tone: str = "neutral") -> str:
    safe_label = escape(label)
    safe_tone = escape(tone)
    return f'<span class="status-badge status-badge--{safe_tone}">{safe_label}</span>'


def render_page_header(
    title: str,
    subtitle: str,
    *,
    eyebrow: str | None = None,
    badge_label: str | None = None,
    badge_tone: str = "neutral",
) -> None:
    eyebrow_html = (
        f'<div class="page-header__eyebrow">{escape(eyebrow)}</div>' if eyebrow else ""
    )
    badge = badge_html(badge_label, badge_tone) if badge_label else ""
    st.markdown(
        f"""
        <section class="page-header">
          {eyebrow_html}
          <div class="page-header__row">
            <div>
              <h1>{escape(title)}</h1>
              <p>{escape(subtitle)}</p>
            </div>
            <div>{badge}</div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(
    title: str,
    subtitle: str,
    *,
    badge_label: str | None = None,
    badge_tone: str = "neutral",
) -> None:
    badge = badge_html(badge_label, badge_tone) if badge_label else ""
    st.markdown(
        f"""
        <div class="section-header">
          <div>
            <h3>{escape(title)}</h3>
            <p>{escape(subtitle)}</p>
          </div>
          <div>{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(items: list[dict[str, Any]]) -> None:
    columns = st.columns(len(items))
    for column, item in zip(columns, items):
        delta = item.get("delta")
        tone = item.get("tone", "neutral")
        delta_html = (
            (
                f'<div class="kpi-card__delta kpi-card__delta--{escape(tone)}">'
                f"{escape(str(delta))}</div>"
            )
            if delta
            else ""
        )
        column.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-card__label">{escape(str(item['label']))}</div>
              <div class="kpi-card__value">{escape(str(item['value']))}</div>
              {delta_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_empty_state(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
          <div class="empty-state__label">No content yet</div>
          <h3>{escape(title)}</h3>
          <p>{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_api_error_state(exc: Exception, *, resource: str) -> None:
    message = str(exc)
    if isinstance(exc, APIClientError):
        if "Connection refused" in message or "Failed to establish a new connection" in message:
            title = "Backend unavailable"
            body = (
                f"The app is configured to use the API for {resource}, "
                "but the backend is not reachable. "
                "Start the API server or switch to mock mode for a fully guided UI demo."
            )
        elif "404" in message:
            title = "API connected, endpoint not ready yet"
            body = (
                f"The backend responded, but the endpoint needed for {resource} "
                "is not implemented yet. "
                "The visual flow remains available, but this section cannot load "
                "live API data for now."
            )
        else:
            title = "Data could not be loaded"
            body = (
                f"The app could not fetch {resource} from the API. "
                "This is shown as a product-style fallback so the UI stays "
                "readable during development."
            )
    else:
        title = "Something unexpected happened"
        body = f"An unexpected error occurred while loading {resource}."

    render_empty_state(title, body)
    st.caption(message)


def render_info_card(title: str, body: str, *, tone: str = "neutral") -> None:
    st.markdown(
        f"""
        <div class="info-card info-card--{escape(tone)}">
          <strong>{escape(title)}</strong>
          <p>{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_label_value_pairs(items: list[tuple[str, str]]) -> None:
    rows = "".join(
        (
            '<div class="detail-row">'
            f'<span class="detail-row__label">{escape(label)}</span>'
            f'<span class="detail-row__value">{escape(value)}</span>'
            "</div>"
        )
        for label, value in items
    )
    st.markdown(f'<div class="detail-grid">{rows}</div>', unsafe_allow_html=True)


def dataframe_with_default_style(df: pd.DataFrame) -> Any:
    return df.style.set_properties(
        **{
            "background-color": "#ffffff",
            "border-color": "#d7e3eb",
            "color": "#12354a",
        }
    )


def style_action_outcome_table(df: pd.DataFrame) -> Any:
    styled = dataframe_with_default_style(df)
    if "Action" in df.columns:
        styled = styled.map(
            lambda value: (
                "color: #18794e; font-weight: 700;"
                if str(value).upper() == "BUY"
                else "color: #b5474f; font-weight: 700;"
                if str(value).upper() == "SELL"
                else ""
            ),
            subset=["Action"],
        )
    if "Outcome" in df.columns:
        styled = styled.map(
            lambda value: (
                "color: #1f6074; font-weight: 700;"
                if str(value).upper() == "YES"
                else "color: #9f5b18; font-weight: 700;"
                if str(value).upper() == "NO"
                else ""
            ),
            subset=["Outcome"],
        )
    return styled
