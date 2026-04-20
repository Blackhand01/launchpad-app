"""Launchpad — Streamlit entry point (mobile-first, two-phase AI flow)."""

from __future__ import annotations

import html
import os
import re
from typing import Any

import resend
import streamlit as st
from dotenv import load_dotenv

import ai_engine
import database

load_dotenv()

st.set_page_config(
    page_title="Launchpad",
    layout="centered",
    initial_sidebar_state="expanded",
)

MOBILE_CSS = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {visibility: hidden;}
div[data-testid="stToolbar"] {visibility: hidden;}
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 720px;}
button {min-height: 48px; font-size: 1.05rem;}
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
  font-size: 1.05rem !important;
  min-height: 44px;
}
[data-testid="stTabs"] button {min-height: 44px;}
div[data-testid="column"] .stButton > button {white-space: nowrap;}
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

WEEKLY_LIMIT_MESSAGE = "Weekly limit reached! Contact Stefano to get more credits."


def _notify_admin_new_signup(email: str) -> None:
    key = os.getenv("RESEND_API_KEY")
    to_addr = os.getenv("ADMIN_NOTIFICATION_EMAIL")
    from_addr = os.getenv("RESEND_FROM_EMAIL")
    if not key or not to_addr or not from_addr:
        return
    resend.api_key = key
    resend.Emails.send(
        {
            "from": from_addr,
            "to": [to_addr],
            "subject": "Launchpad: nuova richiesta di accesso",
            "html": f"<p>Nuovo utente registrato: <strong>{email}</strong></p>"
            "<p>Approvazione richiesta in Supabase (<code>profiles.is_approved</code>).</p>",
        }
    )


def _notify_high_vision_alert(
    *,
    idea_title: str,
    author_email: str,
    vision_score: int,
    feasibility_score: int,
) -> None:
    if vision_score <= 80:
        return
    key = os.getenv("RESEND_API_KEY")
    to_addr = os.getenv("HIGH_VISION_ALERT_EMAIL") or os.getenv("ADMIN_NOTIFICATION_EMAIL")
    from_addr = os.getenv("RESEND_FROM_EMAIL")
    if not key or not to_addr or not from_addr:
        return
    resend.api_key = key
    resend.Emails.send(
        {
            "from": from_addr,
            "to": [to_addr],
            "subject": f"Launchpad: vision alta ({vision_score}) — {idea_title[:80]}",
            "html": (
                f"<p><strong>Vision score:</strong> {vision_score} · "
                f"<strong>Feasibility:</strong> {feasibility_score}</p>"
                f"<p><strong>Idea:</strong> {idea_title}</p>"
                f"<p><strong>Autore:</strong> {author_email}</p>"
            ),
        }
    )


def _auth_client() -> Any | None:
    if "sb_access" not in st.session_state or "sb_refresh" not in st.session_state:
        return None
    return database.user_client(st.session_state["sb_access"], st.session_state["sb_refresh"])


def _sign_out() -> None:
    for k in (
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
        st.session_state.pop(k, None)


def _require_env_for_ai() -> None:
    missing = [k for k in ("OPENAI_API_KEY",) if not os.getenv(k)]
    if missing:
        st.warning("Imposta le chiavi API in `.env`: " + ", ".join(missing))
    if not os.getenv("GEMINI_API_KEY"):
        st.info("`GEMINI_API_KEY` non impostata: il blueprint userà solo Groq (niente fallback da Gemini).")
    if not os.getenv("GROQ_API_KEY"):
        st.info(
            "`GROQ_API_KEY` non impostata: trascrizione audio e fallback blueprint su quota Gemini non disponibili."
        )


def _score_color(score: int) -> str:
    if score <= 39:
        return "#f59e0b"
    if score <= 69:
        return "#f6c343"
    return "#2e8b57"


def _to_thirtieth(score: float | int | None) -> float:
    raw = 0.0 if score is None else float(score)
    clamped = max(0.0, min(100.0, raw))
    return round(clamped * 0.3, 1)


def _fmt_thirtieth(score: float | int | None) -> str:
    v = _to_thirtieth(score)
    if float(v).is_integer():
        return f"{int(v)}/30"
    return f"{v:.1f}/30"


def _normalize_outcome(verdict: str) -> str:
    v = str(verdict or "").strip().upper()
    if v == "BUILD":
        return "GO"
    if v == "ITERATE":
        return "PIVOT"
    if v in {"GO", "PIVOT", "CAUTION", "NOT NOW"}:
        return v
    return "NOT NOW"


def _ui_outcome_copy(verdict: str) -> tuple[str, str, str]:
    v = _normalize_outcome(verdict)
    if v == "GO":
        return "GO", "Lancio consigliato", "#50C878"
    if v == "PIVOT":
        return "PIVOT", "Idea valida, esecuzione da rivedere", "#FFD700"
    if v == "CAUTION":
        return "CAUTION", "Costruibile, ma molti vincoli", "#FF7F00"
    return "NOT NOW", "Poche chance di successo ora", "#DC143C"


def _compute_row_decision(row: dict[str, Any]) -> dict[str, float | int | str]:
    vision = int(row.get("vision_score") or 0)
    feasibility = int(row.get("feasibility_score") or 0)
    dependency_raw = row.get("dependency_score")
    dependency = 50 if dependency_raw is None else int(dependency_raw)
    computed = ai_engine.compute_yc_decision(vision, feasibility, dependency)
    computed["yc_verdict"] = _normalize_outcome(str(computed.get("yc_verdict") or ""))
    return computed


def _legacy_storage_outcome(verdict: str) -> str:
    v = _normalize_outcome(verdict)
    if v == "GO":
        return "BUILD"
    if v in {"PIVOT", "CAUTION"}:
        return "ITERATE"
    return "NOT NOW"


def _strip_pivot_from_analysis(report: str) -> str:
    txt = str(report or "")
    if not txt.strip():
        return ""
    pivot_heading = re.search(
        r"(?im)^\s*(?:#{1,6}\s*)?(?:pivot suggestion|suggerimento pivot|piano pratico 14 giorni)\s*:?\s*$",
        txt,
    )
    if not pivot_heading:
        return txt
    return txt[: pivot_heading.start()].rstrip()


def _render_score_block(label: str, score: int) -> None:
    st.metric(label, _fmt_thirtieth(score))
    safe_score = min(max(int(score), 0), 100)
    color = _score_color(safe_score)
    st.markdown(
        (
            "<div style='width:100%;height:14px;background:#eceff3;border-radius:999px;overflow:hidden;'>"
            f"<div style='width:{safe_score}%;height:100%;background:{color};'></div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_tabbed_report(row: dict[str, Any], *, read_only_caption: bool = False) -> None:
    """Tabs: score, analysis (sandwich), pivot."""
    if read_only_caption:
        st.caption("Sola lettura · nessuna modifica dopo la validazione")
    t_score, t_analysis, t_pivot = st.tabs(["Decisione", "Analisi", "Piano 14 giorni"])
    vision = row.get("vision_score")
    feas = row.get("feasibility_score")
    with t_score:
        if vision is None or feas is None:
            st.info("Punteggi non ancora disponibili per questa idea.")
        else:
            decision = _compute_row_decision(row)
            yc_verdict = str(decision["yc_verdict"])
            verdict_title, verdict_hint, verdict_color = _ui_outcome_copy(yc_verdict)
            vision_score = int(decision["vision_score"])
            raw_feasibility = int(decision["feasibility_score"])
            dependency_score = int(decision["dependency_score"])
            real_feasibility = float(decision["real_feasibility"])
            final_score = float(decision["final_score"])

            st.markdown(
                (
                    "<div style='margin-top:4px;margin-bottom:14px;padding:14px 16px;border-radius:12px;"
                    "border:1px solid #1f2937;background:linear-gradient(135deg,#0f172a,#111827);'>"
                    "<div style='font-size:0.85rem;color:#cbd5e1;'>Esito</div>"
                    f"<div style='font-size:2.0rem;font-weight:800;line-height:1.1;color:{verdict_color};'>"
                    f"{html.escape(verdict_title)}</div>"
                    f"<div style='margin-top:4px;color:#d1d5db;'>{html.escape(verdict_hint)}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("Visione", _fmt_thirtieth(vision_score))
            c2.metric("Fattibilità grezza", _fmt_thirtieth(raw_feasibility))
            c3.metric("Rischio dipendenze", _fmt_thirtieth(dependency_score))

            _render_score_block("Fattibilità reale", int(round(real_feasibility)))
            _render_score_block("Score finale", int(round(final_score)))
            with st.expander("Perché è uscito questo esito"):
                st.write(
                    f"- Visione: **{_fmt_thirtieth(vision_score)}** indica il potenziale di lungo periodo."
                )
                st.write(
                    f"- Fattibilità grezza: **{_fmt_thirtieth(raw_feasibility)}** riflette quanto è costruibile subito."
                )
                st.write(
                    f"- Rischio dipendenze: **{_fmt_thirtieth(dependency_score)}** segnala quanto dipendi da fattori esterni."
                )
                st.write(
                    f"- Esito mostrato: **{verdict_title}**."
                )
    with t_analysis:
        report = row.get("analysis_report") or ""
        clean_report = _strip_pivot_from_analysis(report)
        if clean_report.strip():
            st.markdown(clean_report)
        else:
            st.write("—")
    with t_pivot:
        pivot = row.get("pivot_suggestion") or ""
        if pivot.strip():
            safe_pivot = html.escape(pivot).replace("\n", "<br>")
            st.markdown(
                (
                    "<div style='background:#eef6ff;border:1px solid #bfdcff;border-radius:12px;"
                    "padding:14px 16px;line-height:1.5;color:#111111;'>"
                    f"<strong style='color:#111111;'>Piano pratico 14 giorni:</strong><br>{safe_pivot}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        else:
            st.write("—")


def page_auth() -> bool:
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
                    _notify_admin_new_signup(email)
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
        _sign_out()
        st.rerun()


def _run_validation_for_idea(sb: Any, user_id: str, row: dict[str, Any]) -> None:
    """Run Phase 2 validation, persist results, and notify on high vision score."""
    with st.status("Validazione in corso…", expanded=True) as status:

        def hook(msg: str) -> None:
            status.write(msg)

        result = ai_engine.run_feasibility_validation(
            row["structured_data"],
            status_writer=hook,
        )

    fields = {
        "analysis_report": result["reasoning"],
        "vision_score": result["vision_score"],
        "feasibility_score": result["feasibility_score"],
        "dependency_score": result["dependency_score"],
        "real_feasibility": result["real_feasibility"],
        "final_score": result["final_score"],
        "yc_verdict": result["yc_verdict"],
        "pivot_suggestion": result["pivot_suggestion"],
        "thought_log": result["thought_log"],
        "status": "validated",
    }
    try:
        database.update_idea(sb, str(row["id"]), user_id, fields)
    except Exception as e:  # noqa: BLE001
        err = str(e).lower()
        if (
            "23514" in err
            and "yc_verdict" in err
            and ("ideas_yc_verdict_check" in err or "ideas_yc_verdict_values" in err)
        ):
            compat_fields = dict(fields)
            compat_fields["yc_verdict"] = _legacy_storage_outcome(str(fields.get("yc_verdict") or "NOT NOW"))
            database.update_idea(sb, str(row["id"]), user_id, compat_fields)
            st.info(
                "Compatibilità DB attiva: applica la migrazione `schema.sql` per usare i nuovi esiti "
                "`GO/PIVOT/CAUTION/NOT NOW` anche a livello database."
            )
        else:
            raise
    profile = database.fetch_profile(sb, user_id) or {}
    _notify_high_vision_alert(
        idea_title=str(row.get("title") or ""),
        author_email=str(profile.get("email") or st.session_state.get("user_email") or ""),
        vision_score=int(result["vision_score"]),
        feasibility_score=int(result["feasibility_score"]),
    )
    st.success("Validazione completata.")
    st.rerun()


def _render_nav_bar(profile: dict[str, Any], user_email: str) -> str:
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
            _sign_out()
            st.rerun()

    if selected not in pages:
        st.session_state["nav_page"] = pages[0]
        selected = pages[0]

    if st.session_state.get("nav_page") != selected:
        st.session_state["nav_page"] = selected

    st.divider()
    return str(selected)


def page_console(sb: Any, user_id: str) -> None:
    st.header("Dashboard")
    st.caption("Storico idee · puoi modificare blueprint e validare quando vuoi")
    ideas = database.list_my_ideas(sb, user_id)
    if not ideas:
        st.write("Nessuna idea ancora. Vai su **Nuova idea** per iniziare.")
        return

    labels = [f"{(i.get('title') or 'Senza titolo')[:52]} · {str(i['id'])[:8]}…" for i in ideas]
    choice = st.selectbox("Le tue idee", labels, label_visibility="visible")
    idx = labels.index(choice)
    idea_id = ideas[idx]["id"]
    row = database.get_idea(sb, idea_id, user_id)
    if not row:
        st.error("Idea non trovata.")
        return

    st.divider()
    ycv = "—"
    if row.get("vision_score") is not None and row.get("feasibility_score") is not None:
        ycv_raw = str(_compute_row_decision(row).get("yc_verdict") or "—")
        ycv = _ui_outcome_copy(ycv_raw)[0] if ycv_raw != "—" else "—"
    st.markdown(
        f"**Stato:** `{row['status']}` · **Esito:** `{ycv}`"
    )

    if row.get("status") == "raw" and not row.get("structured_data"):
        st.info("Questa idea non ha ancora un blueprint. Aprila da **Nuova idea** per generarlo.")

    if row.get("structured_data") and row.get("status") != "validated":
        edit_mode = st.toggle("Modalità modifica blueprint", key=f"console_edit_{idea_id}", value=False)
        if edit_mode:
            sd = row["structured_data"]
            c_problem = st.text_area(
                "Problem",
                value=sd.get("problem", ""),
                height=100,
                key=f"console_problem_{idea_id}",
            )
            c_solution = st.text_area(
                "Solution",
                value=sd.get("solution", ""),
                height=100,
                key=f"console_solution_{idea_id}",
            )
            c_kf = sd.get("key_features") or []
            c_kf_text = st.text_area(
                "Key features (una per riga)",
                value="\n".join(str(x) for x in c_kf),
                height=120,
                key=f"console_kf_{idea_id}",
            )
            if st.button("Salva modifiche blueprint", type="secondary", key=f"console_save_{idea_id}"):
                c_lines = [ln.strip() for ln in c_kf_text.splitlines() if ln.strip()]
                database.update_idea(
                    sb,
                    str(idea_id),
                    user_id,
                    {
                        "structured_data": {
                            "problem": c_problem,
                            "solution": c_solution,
                            "key_features": c_lines,
                        },
                        "status": "ready_for_validation",
                    },
                )
                st.success("Blueprint salvato. Ora puoi lanciare la validazione.")
                st.rerun()
        else:
            with st.expander("Blueprint"):
                st.json(row["structured_data"])
    elif row.get("structured_data"):
        with st.expander("Blueprint"):
            st.json(row["structured_data"])

    row = database.get_idea(sb, idea_id, user_id) or row
    if row.get("status") == "ready_for_validation" and row.get("structured_data"):
        st.markdown("### Validazione idea")
        if st.button("Lancia validazione", type="primary", key=f"console_validate_{idea_id}"):
            try:
                _run_validation_for_idea(sb, user_id, row)
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
                return
    elif row.get("status") == "pending_confirmation" and row.get("structured_data"):
        st.info("Per attivare la validazione, salva prima il blueprint.")

    render_tabbed_report(row, read_only_caption=False)


def _new_idea_flow(sb: Any, user_id: str) -> None:
    st.subheader("Nuova idea")
    _require_env_for_ai()

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
                    bp = ai_engine.build_product_blueprint(transcript)
                bp_model = str(bp.pop("_model_used", "sconosciuto"))
                database.update_idea(
                    sb,
                    new_id,
                    user_id,
                    {"structured_data": bp, "status": "pending_confirmation"},
                )
                models_by_idea = dict(st.session_state.get("blueprint_models_by_idea") or {})
                models_by_idea[new_id] = bp_model
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
            st.success(f"Blueprint pronto ({bp_model}): rivedi e conferma.")
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
                bp = ai_engine.build_product_blueprint(row["raw_transcript"])
            bp_model = str(bp.pop("_model_used", "sconosciuto"))
            database.update_idea(
                sb,
                idea_id,
                user_id,
                {"structured_data": bp, "status": "pending_confirmation"},
            )
            models_by_idea = dict(st.session_state.get("blueprint_models_by_idea") or {})
            models_by_idea[str(idea_id)] = bp_model
            st.session_state["blueprint_models_by_idea"] = models_by_idea
            st.success(f"Blueprint rigenerato con `{bp_model}`.")
            st.rerun()

    if row.get("status") == "pending_confirmation" and row.get("structured_data"):
        st.markdown("### Conferma blueprint")
        model_used = (st.session_state.get("blueprint_models_by_idea") or {}).get(str(idea_id))
        if model_used:
            st.caption(f"Blueprint generato con: `{model_used}`")
        st.info("Did I get this right? Feel free to fix any details before the final check.")
        sd = row["structured_data"]
        problem = st.text_area(
            "Problem",
            value=sd.get("problem", ""),
            height=100,
            key=f"nb_problem_{idea_id}",
        )
        solution = st.text_area(
            "Solution",
            value=sd.get("solution", ""),
            height=100,
            key=f"nb_solution_{idea_id}",
        )
        kf = sd.get("key_features") or []
        kf_text = st.text_area(
            "Key features (una per riga)",
            value="\n".join(str(x) for x in kf),
            height=120,
            key=f"nb_kf_{idea_id}",
        )
        if st.button("Salva modifiche blueprint", type="secondary"):
            lines = [ln.strip() for ln in kf_text.splitlines() if ln.strip()]
            database.update_idea(
                sb,
                idea_id,
                user_id,
                {
                    "structured_data": {
                        "problem": problem,
                        "solution": solution,
                        "key_features": lines,
                    },
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
                _run_validation_for_idea(sb, user_id, row)
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
                return


def page_new_idea(sb: Any, user_id: str) -> None:
    st.header("Pipeline")
    _new_idea_flow(sb, user_id)


def page_admin(sb: Any, profile: dict[str, Any]) -> None:
    if not profile.get("is_admin"):
        st.error("Accesso negato.")
        return
    st.header("Admin")
    st.caption("Reset quota manuale, Hall of Fame, utenti.")

    st.subheader("Reset crediti settimanali")
    st.write("Azzera `ideas_this_week` per tutti o per un utente (RPC con controllo admin).")
    if st.button("Reset tutti gli utenti", type="primary"):
        try:
            n = database.admin_reset_ideas_this_week(sb, None)
            st.success(f"Utenti aggiornati: {n}")
        except Exception as e:  # noqa: BLE001
            st.error(str(e))
    profiles = database.admin_list_profiles()
    user_emails = {p["id"]: p.get("email") or p["id"] for p in profiles}
    pick = st.selectbox("Reset singolo utente", list(user_emails.keys()), format_func=lambda uid: user_emails[uid])
    if st.button("Reset utente selezionato"):
        try:
            n = database.admin_reset_ideas_this_week(sb, str(pick))
            st.success(f"Righe aggiornate: {n}")
        except Exception as e:  # noqa: BLE001
            st.error(str(e))

    st.subheader("Hall of Fame")
    try:
        hof = database.admin_hall_of_fame()
    except Exception as e:  # noqa: BLE001
        st.warning(
            "Hall of Fame non disponibile: probabilmente non hai ancora applicato la migrazione DB v2.5 "
            "(colonne scoring idea: `vision_score`, `dependency_score`, `real_feasibility`, ecc.)."
        )
        st.code(str(e))
        hof = []
    if not hof:
        st.write("Nessuna idea validata con punteggio ancora (o migrazione DB non applicata).")
    else:
        for item in hof:
            title = item.get("title") or "Senza titolo"
            vs = item.get("vision_score")
            fs = item.get("feasibility_score")
            ds = item.get("dependency_score")
            rf = item.get("real_feasibility")
            fin = item.get("final_score")
            ycv = _ui_outcome_copy(str(item.get("yc_verdict") or ""))[0]
            em = item.get("author_email") or "—"
            st.write(
                f"{title} - final {_fmt_thirtieth(fin)} "
                f"(V:{_fmt_thirtieth(vs)} / F:{_fmt_thirtieth(fs)} / D:{_fmt_thirtieth(ds)} / RF:{_fmt_thirtieth(rf)}) "
                f"- Esito:{ycv} - {em}"
            )

    st.subheader("Utenti e idee")
    for p in profiles:
        cols = st.columns((3, 2, 2, 2, 2, 2))
        cols[0].write(p.get("email") or p["id"])
        cols[1].write("approvato" if p.get("is_approved") else "in attesa")
        cols[2].write("admin" if p.get("is_admin") else "—")
        cols[3].write(f"quota: {p.get('ideas_this_week', 0)}/{p.get('weekly_ideas_limit', 3)}")
        approve_label = "Revoca approv." if p.get("is_approved") else "Approva"
        admin_label = "Rimuovi admin" if p.get("is_admin") else "Rendi admin"
        if cols[4].button(approve_label, key=f"ap_{p['id']}", use_container_width=True):
            database.admin_set_approved(p["id"], not p.get("is_approved"))
            st.rerun()
        if cols[5].button(admin_label, key=f"ad_{p['id']}", use_container_width=True):
            database.admin_set_admin(p["id"], not p.get("is_admin"))
            st.rerun()

    st.subheader("Tutte le idee")
    ideas = database.admin_list_ideas()
    for idea in ideas:
        with st.expander(f"{idea.get('title','')} — {idea['id']}"):
            admin_outcome = _ui_outcome_copy(str(idea.get("yc_verdict") or ""))[0]
            st.write(
                f"user_id: `{idea.get('user_id')}` · status: `{idea.get('status')}` · "
                f"esito: `{admin_outcome}` · "
                f"vision: `{_fmt_thirtieth(idea.get('vision_score'))}` · "
                f"dependency: `{_fmt_thirtieth(idea.get('dependency_score'))}` · "
                f"real_feasibility: `{_fmt_thirtieth(idea.get('real_feasibility'))}`"
            )
            if idea.get("structured_data"):
                st.json(idea["structured_data"])
            if idea.get("analysis_report"):
                st.markdown(idea["analysis_report"])


def main() -> None:
    st.title("Launchpad")
    st.caption("Validazione idee · mobile-first")

    sb = _auth_client()
    if not sb:
        page_auth()
        return

    user_res = sb.auth.get_user()
    user = user_res.user
    if not user:
        _sign_out()
        st.error("Sessione non valida.")
        st.rerun()
        return

    profile = database.fetch_profile(sb, user.id)
    if not profile:
        st.error("Profilo mancante. Controlla il trigger `handle_new_user` su Supabase.")
        if st.button("Esci"):
            _sign_out()
            st.rerun()
        return

    if not profile.get("is_approved"):
        page_pending()
        return

    nav = _render_nav_bar(profile, user.email or "")

    if nav == "Console":
        page_console(sb, user.id)
    elif nav == "Nuova idea":
        page_new_idea(sb, user.id)
    else:
        page_admin(sb, profile)


if __name__ == "__main__":
    main()
