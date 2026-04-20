from __future__ import annotations

import streamlit as st


def apply_base_styles() -> None:
    st.markdown(
        """
<style>
:root {
    --bg: #f4f8fb;
    --bg-elevated: #ffffff;
    --bg-soft: #edf4f8;
    --border: #d6e3eb;
    --border-strong: #b9ced8;
    --text: #12354a;
    --muted: #5b7486;
    --brand: #1f6074;
    --brand-soft: #d7eaf0;
    --success: #18794e;
    --success-soft: #dbf2e5;
    --danger: #b5474f;
    --danger-soft: #f9e1e4;
    --warning: #9f5b18;
    --warning-soft: #f7e7d4;
    --shadow: 0 16px 40px rgba(18, 53, 74, 0.08);
}

html, body, [class*="css"] {
    font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(31, 96, 116, 0.10), transparent 32%),
        linear-gradient(180deg, #f7fbfd 0%, var(--bg) 100%);
}

[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2.5rem;
    max-width: 1200px;
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, #12354a 0%, #19485e 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

[data-testid="stSidebar"] * {
    color: #eef7fb;
}

[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] p {
    color: #d8e7ef;
}

[data-testid="stSidebar"] .stRadio > div {
    gap: 0.35rem;
}

[data-testid="stSidebar"] .stRadio label {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 0.55rem 0.75rem;
}

[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] {
    background: transparent;
    border: none;
    padding: 0;
}

.sidebar-brand {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 20px;
    padding: 1rem 1rem 0.9rem;
    margin-bottom: 1rem;
}

.sidebar-brand__eyebrow {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #b8d3e0;
    margin-bottom: 0.35rem;
}

.sidebar-brand h2 {
    margin: 0;
    font-size: 1.25rem;
    color: #ffffff;
}

.sidebar-brand p {
    margin: 0.45rem 0 0;
    color: #d8e7ef;
    font-size: 0.92rem;
    line-height: 1.45;
}

.sidebar-panel {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 18px;
    padding: 0.9rem 1rem;
    margin-top: 0.85rem;
}

.sidebar-panel p,
.sidebar-panel strong {
    margin: 0;
}

.page-header {
    background: rgba(255, 255, 255, 0.72);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(214, 227, 235, 0.9);
    box-shadow: var(--shadow);
    border-radius: 28px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1.4rem;
}

.page-header__eyebrow {
    color: var(--brand);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.74rem;
    margin-bottom: 0.55rem;
}

.page-header__row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
}

.page-header h1 {
    margin: 0;
    color: var(--text);
    font-size: 2.1rem;
    line-height: 1.05;
}

.page-header p {
    margin: 0.55rem 0 0;
    color: var(--muted);
    max-width: 720px;
    line-height: 1.55;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: end;
    gap: 1rem;
    margin: 0.55rem 0 0.9rem;
}

.section-header h3 {
    margin: 0;
    color: var(--text);
    font-size: 1.15rem;
}

.section-header p {
    margin: 0.3rem 0 0;
    color: var(--muted);
    font-size: 0.95rem;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border-radius: 999px;
    padding: 0.32rem 0.72rem;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: 1px solid transparent;
}

.status-badge--neutral {
    background: var(--bg-soft);
    color: var(--text);
    border-color: var(--border);
}

.status-badge--brand {
    background: var(--brand-soft);
    color: var(--brand);
    border-color: #bfd9e2;
}

.status-badge--success {
    background: var(--success-soft);
    color: var(--success);
    border-color: #c4e8d0;
}

.status-badge--danger {
    background: var(--danger-soft);
    color: var(--danger);
    border-color: #f0c7ce;
}

.status-badge--warning {
    background: var(--warning-soft);
    color: var(--warning);
    border-color: #edd4b6;
}

.kpi-card {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 251, 253, 0.96));
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    border-radius: 22px;
    padding: 1rem 1.1rem;
    min-height: 126px;
}

.kpi-card__label {
    color: var(--muted);
    font-size: 0.84rem;
    margin-bottom: 0.6rem;
}

.kpi-card__value {
    color: var(--text);
    font-size: 1.6rem;
    line-height: 1.1;
    font-weight: 700;
}

.kpi-card__delta {
    margin-top: 0.6rem;
    font-size: 0.88rem;
    font-weight: 600;
}

.kpi-card__delta--success { color: var(--success); }
.kpi-card__delta--danger { color: var(--danger); }
.kpi-card__delta--neutral { color: var(--muted); }

.info-card,
.empty-state,
.hero-panel,
.market-summary,
.spotlight-card {
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 1rem 1.1rem;
    box-shadow: var(--shadow);
}

.info-card p,
.empty-state p,
.hero-panel p,
.market-summary p {
    color: var(--muted);
    margin-bottom: 0;
    line-height: 1.55;
}

.info-card--brand {
    background: linear-gradient(180deg, #f9fdff, #edf7fb);
    border-color: #cbe0e8;
}

.empty-state {
    text-align: center;
    padding: 2rem 1.3rem;
}

.empty-state__label {
    color: var(--brand);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    margin-bottom: 0.55rem;
}

.empty-state h3 {
    margin: 0;
    color: var(--text);
}

.detail-grid {
    display: grid;
    gap: 0.5rem;
}

.detail-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    border-bottom: 1px solid #edf3f7;
    padding-bottom: 0.5rem;
}

.detail-row:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

.detail-row__label {
    color: var(--muted);
}

.detail-row__value {
    color: var(--text);
    font-weight: 600;
    text-align: right;
}

.hero-panel {
    padding: 1.35rem;
}

.hero-panel__eyebrow {
    color: var(--brand);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.72rem;
    margin-bottom: 0.5rem;
}

.hero-panel h2 {
    margin: 0;
    color: var(--text);
    font-size: 2rem;
    line-height: 1.1;
}

.hero-panel__list {
    display: grid;
    gap: 0.7rem;
    margin-top: 1.1rem;
}

.hero-panel__item {
    background: var(--bg-soft);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 0.8rem 0.9rem;
}

.hero-panel__item strong {
    color: var(--text);
}

.market-summary__title {
    font-size: 1.18rem;
    color: var(--text);
    font-weight: 700;
    margin-bottom: 0.55rem;
}

.split-pills {
    display: flex;
    gap: 0.75rem;
    margin: 1rem 0 0.8rem;
}

.split-pill {
    flex: 1;
    border-radius: 18px;
    padding: 0.85rem 0.95rem;
    border: 1px solid var(--border);
}

.split-pill--yes {
    background: #e9f7f0;
    border-color: #c7e7d5;
}

.split-pill--no {
    background: #f8eee8;
    border-color: #edd3c4;
}

.split-pill__label {
    color: var(--muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.split-pill__value {
    color: var(--text);
    font-size: 1.25rem;
    font-weight: 700;
    margin-top: 0.2rem;
}

.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.85rem;
    margin-top: 1rem;
}

.feature-card {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1rem;
}

.feature-card h4 {
    margin: 0 0 0.35rem;
    color: var(--text);
}

.feature-card p {
    margin: 0;
    color: var(--muted);
}

.spotlight-card {
    padding: 1.15rem 1.2rem;
    margin-top: 0.9rem;
}

.spotlight-card__label {
    color: var(--brand);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    margin-bottom: 0.45rem;
}

.spotlight-card__value {
    color: var(--text);
    font-size: 1.65rem;
    font-weight: 700;
    line-height: 1.1;
}

.spotlight-card__body {
    color: var(--muted);
    margin-top: 0.45rem;
    line-height: 1.5;
}

.section-spacer {
    height: 0.65rem;
}

[data-testid="stForm"] {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 1rem 1rem 0.35rem;
    box-shadow: var(--shadow);
}

[data-testid="stTextInputRootElement"] input,
[data-testid="stNumberInput"] input,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    background: #fbfdfe;
    border-radius: 14px;
}

/* Prevent white-on-white text in Streamlit form fields. */
.block-container [data-testid="stTextInputRootElement"] input,
.block-container [data-testid="stNumberInput"] input,
.block-container [data-baseweb="input"] input,
.block-container textarea {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    caret-color: var(--text) !important;
}

.block-container [data-testid="stTextInputRootElement"] input::placeholder,
.block-container [data-testid="stNumberInput"] input::placeholder,
.block-container [data-baseweb="input"] input::placeholder,
.block-container textarea::placeholder {
    color: var(--muted) !important;
    opacity: 0.72 !important;
}

.block-container [data-testid="stTextInput"] label,
.block-container [data-testid="stTextInput"] label p,
.block-container [data-testid="stNumberInput"] label,
.block-container [data-testid="stNumberInput"] label p,
.block-container [data-testid="stCaptionContainer"],
.block-container [data-testid="stCaptionContainer"] p {
    color: var(--muted) !important;
}

/* Ensure Streamlit-native text stays readable across all pages (Trading included). */
.block-container [data-testid="stMarkdownContainer"],
.block-container [data-testid="stMarkdownContainer"] p,
.block-container [data-testid="stMarkdownContainer"] li,
.block-container [data-testid="stMarkdownContainer"] span,
.block-container [data-testid="stMetricLabel"],
.block-container [data-testid="stMetricValue"],
.block-container [data-testid="stMetricDelta"],
.block-container [data-testid="stSelectbox"] label,
.block-container [data-testid="stSelectbox"] label p,
.block-container [data-testid="stSlider"] label,
.block-container [data-testid="stSlider"] label p,
.block-container [data-testid="stCheckbox"] label,
.block-container [data-testid="stRadio"] label,
.block-container [data-testid="stDownloadButton"] button {
    color: var(--text) !important;
}

.block-container [data-baseweb="select"] * {
    color: var(--text) !important;
}

.block-container [data-baseweb="select"] svg {
    fill: var(--muted) !important;
}

.stButton > button {
    border-radius: 999px;
    border: 1px solid #194b5e;
    background: linear-gradient(180deg, #2f7f98 0%, #1f6074 100%);
    color: #ffffff !important;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.18);
    font-weight: 700;
    padding: 0.55rem 1rem;
    box-shadow: 0 3px 12px rgba(18, 53, 74, 0.22);
}

.stButton > button:hover {
    border-color: #12354a;
    background: linear-gradient(180deg, #388ca7 0%, #245f76 100%);
    color: #ffffff !important;
}

.stButton > button:focus,
.stButton > button:focus-visible {
    outline: 3px solid rgba(31, 96, 116, 0.28);
    outline-offset: 1px;
    color: #ffffff !important;
}

[data-testid="stTabs"] button[role="tab"] {
    color: var(--text);
    opacity: 1;
}

[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: var(--brand);
}

.stDownloadButton > button {
    border-radius: 999px;
    border: 1px solid var(--border);
    background: white;
    color: var(--text);
    font-weight: 600;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: var(--shadow);
}

@media (max-width: 900px) {
    .page-header__row,
    .section-header,
    .split-pills,
    .feature-grid {
        display: block;
    }

    .split-pill,
    .feature-card {
        margin-bottom: 0.75rem;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )
