"""Top navigation for authenticated users."""

from __future__ import annotations

from typing import Any

import streamlit as st

from launchpad.auth import sign_out


def render_nav_bar(profile: dict[str, Any], user_email: str) -> str:
    pages = ["Console", "Nuova idea"]
    if profile.get("is_admin"):
        pages.append("Admin")

    st.caption(f"Utente: {profile.get('email') or user_email}")
    current = st.session_state.get("nav_page")
    if current not in pages:
        st.session_state["nav_page"] = pages[0]

    nav_col, logout_col = st.columns((5, 2), gap="small")
    with nav_col:
        selected = st.segmented_control(
            "Navigazione",
            pages,
            key="nav_page",
            label_visibility="collapsed",
            width="stretch",
        )
    with logout_col:
        if st.button("Esci", key="nav_logout", use_container_width=True):
            sign_out()
            st.rerun()

    if selected not in pages:
        st.session_state["nav_page"] = pages[0]
        selected = pages[0]

    if st.session_state.get("nav_page") != selected:
        st.session_state["nav_page"] = selected

    st.divider()
    return str(selected)

