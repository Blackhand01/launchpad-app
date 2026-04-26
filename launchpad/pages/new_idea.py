"""Idea creation and validation pipeline page."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

import ai_engine
import database
from launchpad.config import WEEKLY_LIMIT_MESSAGE
from launchpad.reports import render_tabbed_report
from launchpad.ui.blueprint import render_blueprint_editor
from launchpad.validation import run_validation_for_idea


def require_env_for_ai() -> None:
    missing = [key for key in ("OPENAI_API_KEY",) if not os.getenv(key)]
    if missing:
        st.warning("Imposta le chiavi API in `.env`: " + ", ".join(missing))
    if not os.getenv("GEMINI_API_KEY"):
        st.info("`GEMINI_API_KEY` non impostata: il blueprint userà solo Groq (niente fallback da Gemini).")
    if not os.getenv("GROQ_API_KEY"):
        st.info(
            "`GROQ_API_KEY` non impostata: trascrizione audio e fallback blueprint su quota Gemini non disponibili."
        )


def page_new_idea(sb: Any, user_id: str) -> None:
    st.header("Pipeline")
    _new_idea_flow(sb, user_id)


def _new_idea_flow(sb: Any, user_id: str) -> None:
    st.subheader("Nuova idea")
    require_env_for_ai()

    idea_id = st.session_state.get("active_idea_id")

    if not idea_id:
        st.caption("Fase 1 · Trascrizione Groq + blueprint Gemini (fallback Groq su quota).")
        title = st.text_input(
            "Titolo idea",
            placeholder="Es. App di micro-learning per meccanici",
            key="new_idea_title",
        )
        audio = st.file_uploader(
            "Audio (stream of consciousness)",
            type=["wav", "mp3", "m4a", "aac", "flac"],
            key="new_idea_audio",
        )
        raw_fallback = st.text_area(
            "Oppure incolla testo / appunti",
            height=160,
            key="new_idea_notes",
        )

        if st.button("Genera blueprint", type="primary"):
            if not title.strip():
                st.error("Il titolo è obbligatorio.")
                return
            transcript = ""
            if audio is not None:
                with st.spinner("Trascrizione con Groq Whisper…"):
                    transcript = ai_engine.transcribe_audio_streamlit_file(audio)
            elif raw_fallback.strip():
                transcript = raw_fallback.strip()
            else:
                st.error("Carica un audio oppure incolla del testo.")
                return
            try:
                row = database.create_idea_with_quota(
                    sb,
                    title=title.strip(),
                    raw_transcript=transcript,
                    status="raw",
                )
            except database.MissingRpcError as e:
                st.error(
                    "Migrazione DB mancante: non trovo la funzione Supabase per la quota settimanale.\n\n"
                    "Esegui il blocco v2.5 in `schema.sql` (RPC + colonne), poi fai refresh dello schema API "
                    "in Supabase (Restart/Reload)."
                )
                st.code(str(e))
                return
            except database.WeeklyQuotaReachedError:
                st.error(WEEKLY_LIMIT_MESSAGE)
                return
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
                return
            if not row.get("id"):
                st.error("Creazione idea fallita.")
                return
            new_id = str(row["id"])
            try:
                with st.spinner("Blueprint con Gemini (fallback Groq)…"):
                    blueprint = ai_engine.build_product_blueprint(transcript)
                blueprint_model = str(blueprint.pop("_model_used", "sconosciuto"))
                database.update_idea(
                    sb,
                    new_id,
                    user_id,
                    {"structured_data": blueprint, "status": "pending_confirmation"},
                )
                models_by_idea = dict(st.session_state.get("blueprint_models_by_idea") or {})
                models_by_idea[new_id] = blueprint_model
                st.session_state["blueprint_models_by_idea"] = models_by_idea
            except Exception as e:  # noqa: BLE001
                st.warning(
                    "Idea creata ma il blueprint non è stato generato. "
                    "Puoi riprovare il blueprint senza consumare un altro credito."
                )
                st.error(str(e))
                st.session_state["active_idea_id"] = new_id
                st.rerun()
                return
            st.session_state["active_idea_id"] = new_id
            st.success(f"Blueprint pronto ({blueprint_model}): rivedi e conferma.")
            st.rerun()
        return

    row = database.get_idea(sb, idea_id, user_id)
    if not row:
        st.session_state.pop("active_idea_id", None)
        st.warning("Idea non trovata.")
        return

    if row.get("status") == "validated":
        st.success("Validazione completata.")
        render_tabbed_report(row)
        if st.button("Archivia e crea un’altra idea", type="primary"):
            st.session_state.pop("active_idea_id", None)
            st.session_state.pop("new_idea_title", None)
            st.session_state.pop("new_idea_notes", None)
            st.session_state.pop("new_idea_audio", None)
            st.rerun()
        return

    if row.get("status") == "raw" and not row.get("structured_data"):
        st.warning("Blueprint mancante dopo la creazione. Puoi generarlo ora.")
        if st.button("Riprova blueprint", type="primary"):
            if not row.get("raw_transcript"):
                st.error("Trascrizione mancante.")
                return
            with st.spinner("Blueprint con Gemini (fallback Groq)…"):
                blueprint = ai_engine.build_product_blueprint(row["raw_transcript"])
            blueprint_model = str(blueprint.pop("_model_used", "sconosciuto"))
            database.update_idea(
                sb,
                idea_id,
                user_id,
                {"structured_data": blueprint, "status": "pending_confirmation"},
            )
            models_by_idea = dict(st.session_state.get("blueprint_models_by_idea") or {})
            models_by_idea[str(idea_id)] = blueprint_model
            st.session_state["blueprint_models_by_idea"] = models_by_idea
            st.success(f"Blueprint rigenerato con `{blueprint_model}`.")
            st.rerun()

    if row.get("status") == "pending_confirmation" and row.get("structured_data"):
        st.markdown("### Conferma blueprint")
        model_used = (st.session_state.get("blueprint_models_by_idea") or {}).get(str(idea_id))
        if model_used:
            st.caption(f"Blueprint generato con: `{model_used}`")
        st.info("Did I get this right? Feel free to fix any details before the final check.")
        blueprint = render_blueprint_editor(str(idea_id), row["structured_data"], key_prefix="nb")
        if st.button("Salva modifiche blueprint", type="secondary"):
            database.update_idea(
                sb,
                idea_id,
                user_id,
                {
                    "structured_data": blueprint,
                    "status": "ready_for_validation",
                },
            )
            st.success("Blueprint salvato. Ora puoi lanciare la validazione.")
            st.rerun()

    row = database.get_idea(sb, idea_id, user_id) or row
    if row.get("status") == "ready_for_validation" and row.get("structured_data"):
        st.markdown("### Fase 2 · GPT + ricerca web")
        st.caption("Blueprint già confermato. Premi sotto per avviare la validazione.")
        if st.button("Lancia validazione", type="primary"):
            try:
                run_validation_for_idea(sb, user_id, row)
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
                return

