"""Validation orchestration and persistence."""

from __future__ import annotations

from typing import Any

import streamlit as st

import ai_engine
import database
from launchpad.notifications import notify_high_vision_alert
from launchpad.scoring import legacy_storage_outcome


def run_validation_for_idea(sb: Any, user_id: str, row: dict[str, Any]) -> None:
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
            compat_fields["yc_verdict"] = legacy_storage_outcome(str(fields.get("yc_verdict") or "NOT NOW"))
            database.update_idea(sb, str(row["id"]), user_id, compat_fields)
            st.info(
                "Compatibilità DB attiva: applica la migrazione `schema.sql` per usare i nuovi esiti "
                "`GO/PIVOT/CAUTION/NOT NOW` anche a livello database."
            )
        else:
            raise
    profile = database.fetch_profile(sb, user_id) or {}
    notify_high_vision_alert(
        idea_title=str(row.get("title") or ""),
        author_email=str(profile.get("email") or st.session_state.get("user_email") or ""),
        vision_score=int(result["vision_score"]),
        feasibility_score=int(result["feasibility_score"]),
    )
    st.success("Validazione completata.")
    st.rerun()

