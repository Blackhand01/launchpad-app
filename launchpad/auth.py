"""Authentication UI and session helpers."""

from __future__ import annotations

from typing import Any

import streamlit as st

import database
from launchpad.notifications import notify_admin_new_signup


def auth_client() -> Any | None:
    if "sb_access" not in st.session_state or "sb_refresh" not in st.session_state:
        return None
    return database.user_client(st.session_state["sb_access"], st.session_state["sb_refresh"])


def sign_out() -> None:
    for key in (
        "sb_access",
        "sb_refresh",
        "user_id",
        "user_email",
        "active_idea_id",
        "history_idea_id",
        "new_idea_title",
        "new_idea_notes",
        "new_idea_audio",
        "blueprint_models_by_idea",
    ):
        st.session_state.pop(key, None)


def page_auth() -> None:
    st.subheader("Accesso")
    tab_in, tab_up = st.tabs(["Accedi", "Registrati"])
    client = database.anon_supabase()

    with tab_in:
        with st.form("form_signin", clear_on_submit=False):
            st.text_input("Email", key="in_email", autocomplete="email")
            st.text_input(
                "Password",
                type="password",
                key="in_pw",
                autocomplete="current-password",
            )
            submitted_in = st.form_submit_button("Entra")
        if submitted_in:
            email = (st.session_state.get("in_email") or "").strip()
            password = st.session_state.get("in_pw") or ""
            if not email or not password:
                st.error(
                    "Email o password mancanti. Se il browser ha compilato i campi in automatico, "
                    "clicca in ciascun campo (o premi Tab) e riprova: Streamlit a volte non riceve "
                    "l’autocompilamento finché il focus non passa dai campi."
                )
            else:
                try:
                    res = client.auth.sign_in_with_password({"email": email, "password": password})
                    sess = res.session
                    if not sess:
                        st.error("Accesso non completato (verifica email se richiesta da Supabase).")
                    else:
                        st.session_state["sb_access"] = sess.access_token
                        st.session_state["sb_refresh"] = sess.refresh_token
                        st.session_state["user_id"] = res.user.id
                        st.session_state["user_email"] = res.user.email or email
                        st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))

    with tab_up:
        with st.form("form_signup", clear_on_submit=False):
            st.text_input("Email", key="up_email", autocomplete="email")
            st.text_input(
                "Password",
                type="password",
                key="up_pw",
                autocomplete="new-password",
            )
            submitted_up = st.form_submit_button("Crea account")
        if submitted_up:
            email = (st.session_state.get("up_email") or "").strip()
            password = st.session_state.get("up_pw") or ""
            if not email or not password:
                st.error("Inserisci email e password per registrarti.")
            else:
                try:
                    res = client.auth.sign_up({"email": email, "password": password})
                    notify_admin_new_signup(email)
                    if res.user:
                        st.success(
                            "Account creato. Un amministratore deve approvare l'accesso prima "
                            "che tu possa usare Launchpad."
                        )
                    else:
                        st.info("Controlla la posta per confermare l'account (se abilitato in Supabase).")
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))


def page_pending() -> None:
    st.info(
        "Il tuo account è in attesa di approvazione. "
        "Riceverai accesso quando un amministratore attiverà il profilo."
    )
    if st.button("Esci"):
        sign_out()
        st.rerun()

