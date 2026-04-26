"""Reusable HTML snippets and Streamlit UI components."""

from __future__ import annotations

import html

import streamlit as st

from launchpad.scoring import fmt_thirtieth, score_color


def render_score_block(label: str, score: int) -> None:
    st.metric(label, fmt_thirtieth(score))
    safe_score = min(max(int(score), 0), 100)
    color = score_color(safe_score)
    st.markdown(
        (
            "<div style='width:100%;height:14px;background:#eceff3;border-radius:999px;overflow:hidden;'>"
            f"<div style='width:{safe_score}%;height:100%;background:{color};'></div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def admin_badge_html(label: str, color: str) -> str:
    return f"<span class='admin-badge' style='background:{color};'>{html.escape(label)}</span>"


def admin_rank_html(position: int) -> str:
    if position == 1:
        symbol = "🥇"
    elif position == 2:
        symbol = "🥈"
    elif position == 3:
        symbol = "🥉"
    else:
        symbol = f"#{position}"
    return f"<div class='admin-rank'>{html.escape(symbol)}</div>"


def admin_progress_html(score: float | int | None, label: str = "Final Score") -> str:
    safe_score = max(0.0, min(100.0, float(score or 0)))
    color = score_color(int(round(safe_score)))
    return (
        "<div>"
        f"<div class='admin-progress-label'>{html.escape(label)}</div>"
        "<div class='admin-progress-track'>"
        f"<div class='admin-progress-fill' style='width:{safe_score}%;background:{color};'></div>"
        "</div>"
        f"<div class='admin-progress-value admin-mono'>{html.escape(fmt_thirtieth(score))}</div>"
        "</div>"
    )


def admin_quota_html(used: int, limit: int) -> str:
    safe_limit = max(int(limit or 0), 1)
    safe_used = max(0, min(int(used or 0), safe_limit))
    pct = (safe_used / safe_limit) * 100
    color = "#50C878" if pct < 70 else "#FF7F00" if pct < 100 else "#DC143C"
    return (
        "<div>"
        "<div class='admin-quota-label'>Weekly Quota</div>"
        "<div class='admin-quota-track'>"
        f"<div class='admin-quota-fill' style='width:{pct}%;background:{color};'></div>"
        "</div>"
        f"<div class='admin-quota-value admin-mono'>{safe_used}/{safe_limit}</div>"
        "</div>"
    )

