from __future__ import annotations

import streamlit as st


def apply_base_styles() -> None:
    st.markdown(
        """
<style>
/* Keep styles minimal; avoid custom colors/themes here. */
.block-container { padding-top: 2rem; }
</style>
""",
        unsafe_allow_html=True,
    )
