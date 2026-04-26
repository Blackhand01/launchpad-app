"""Report rendering for validated Launchpad ideas."""

from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

from launchpad.scoring import compute_row_decision, fmt_thirtieth, ui_outcome_copy
from launchpad.ui.components import render_score_block


def strip_pivot_from_analysis(report: str) -> str:
    text = str(report or "")
    if not text.strip():
        return ""
    pivot_heading = re.search(
        r"(?im)^\s*(?:#{1,6}\s*)?(?:pivot suggestion|suggerimento pivot|piano pratico 14 giorni)\s*:?\s*$",
        text,
    )
    if not pivot_heading:
        return text
    return text[: pivot_heading.start()].rstrip()


def render_tabbed_report(row: dict[str, Any], *, read_only_caption: bool = False) -> None:
    """Render score, analysis, and pivot tabs for an idea."""
    if read_only_caption:
        st.caption("Sola lettura · nessuna modifica dopo la validazione")
    t_score, t_analysis, t_pivot = st.tabs(["Decisione", "Analisi", "Piano 14 giorni"])
    vision = row.get("vision_score")
    feasibility = row.get("feasibility_score")
    with t_score:
        if vision is None or feasibility is None:
            st.info("Punteggi non ancora disponibili per questa idea.")
        else:
            decision = compute_row_decision(row)
            yc_verdict = str(decision["yc_verdict"])
            verdict_title, verdict_hint, verdict_color = ui_outcome_copy(yc_verdict)
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
            c1.metric("Visione", fmt_thirtieth(vision_score))
            c2.metric("Fattibilità grezza", fmt_thirtieth(raw_feasibility))
            c3.metric("Rischio dipendenze", fmt_thirtieth(dependency_score))

            render_score_block("Fattibilità reale", int(round(real_feasibility)))
            render_score_block("Score finale", int(round(final_score)))
            with st.expander("Perché è uscito questo esito"):
                st.write(
                    f"- Visione: **{fmt_thirtieth(vision_score)}** indica il potenziale di lungo periodo."
                )
                st.write(
                    f"- Fattibilità grezza: **{fmt_thirtieth(raw_feasibility)}** riflette quanto è costruibile subito."
                )
                st.write(
                    f"- Rischio dipendenze: **{fmt_thirtieth(dependency_score)}** segnala quanto dipendi da fattori esterni."
                )
                st.write(f"- Esito mostrato: **{verdict_title}**.")
    with t_analysis:
        report = row.get("analysis_report") or ""
        clean_report = strip_pivot_from_analysis(report)
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

