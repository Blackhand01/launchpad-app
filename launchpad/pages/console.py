"""User dashboard and idea history page."""

from __future__ import annotations

from typing import Any

import streamlit as st

import database
from launchpad.reports import render_tabbed_report
from launchpad.scoring import compute_row_decision, ui_outcome_copy
from launchpad.ui.blueprint import render_blueprint_editor
from launchpad.validation import run_validation_for_idea


def page_console(sb: Any, user_id: str) -> None:
    st.header("Dashboard")
    st.caption("Storico idee · puoi modificare blueprint e validare quando vuoi")
    ideas = database.list_my_ideas(sb, user_id)
    if not ideas:
        st.write("Nessuna idea ancora. Vai su **Nuova idea** per iniziare.")
        return

    labels = [f"{(idea.get('title') or 'Senza titolo')[:52]} · {str(idea['id'])[:8]}…" for idea in ideas]
    choice = st.selectbox("Le tue idee", labels, label_visibility="visible")
    idx = labels.index(choice)
    idea_id = ideas[idx]["id"]
    row = database.get_idea(sb, idea_id, user_id)
    if not row:
        st.error("Idea non trovata.")
        return

    st.divider()
    outcome = "—"
    if row.get("vision_score") is not None and row.get("feasibility_score") is not None:
        raw_outcome = str(compute_row_decision(row).get("yc_verdict") or "—")
        outcome = ui_outcome_copy(raw_outcome)[0] if raw_outcome != "—" else "—"
    st.markdown(f"**Stato:** `{row['status']}` · **Esito:** `{outcome}`")

    if row.get("status") == "raw" and not row.get("structured_data"):
        st.info("Questa idea non ha ancora un blueprint. Aprila da **Nuova idea** per generarlo.")

    if row.get("structured_data") and row.get("status") != "validated":
        edit_mode = st.toggle("Modalità modifica blueprint", key=f"console_edit_{idea_id}", value=False)
        if edit_mode:
            blueprint = render_blueprint_editor(str(idea_id), row["structured_data"], key_prefix="console")
            if st.button("Salva modifiche blueprint", type="secondary", key=f"console_save_{idea_id}"):
                database.update_idea(
                    sb,
                    str(idea_id),
                    user_id,
                    {
                        "structured_data": blueprint,
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
                run_validation_for_idea(sb, user_id, row)
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
                return
    elif row.get("status") == "pending_confirmation" and row.get("structured_data"):
        st.info("Per attivare la validazione, salva prima il blueprint.")

    render_tabbed_report(row, read_only_caption=False)

