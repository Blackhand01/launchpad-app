"""Launchpad Streamlit entry point."""

from __future__ import annotations

from dotenv import load_dotenv
import streamlit as st

import database
from launchpad.auth import auth_client, page_auth, page_pending, sign_out
from launchpad.pages.admin import page_admin
from launchpad.pages.console import page_console
from launchpad.pages.navigation import render_nav_bar
from launchpad.pages.new_idea import page_new_idea
from launchpad.theme import apply_theme, configure_page


load_dotenv()
configure_page()
apply_theme()


def main() -> None:
    st.title("Launchpad")
    st.caption("Validazione idee · mobile-first")

    sb = auth_client()
    if not sb:
        page_auth()
        return

    user_res = sb.auth.get_user()
    user = user_res.user
    if not user:
        sign_out()
        st.error("Sessione non valida.")
        st.rerun()
        return

    profile = database.fetch_profile(sb, user.id)
    if not profile:
        st.error("Profilo mancante. Controlla il trigger `handle_new_user` su Supabase.")
        if st.button("Esci"):
            sign_out()
            st.rerun()
        return

    if not profile.get("is_approved"):
        page_pending()
        return

    nav = render_nav_bar(profile, user.email or "")

    if nav == "Console":
        page_console(sb, user.id)
    elif nav == "Nuova idea":
        page_new_idea(sb, user.id)
    else:
        page_admin(sb, profile)


if __name__ == "__main__":
    main()
