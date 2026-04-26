"""Admin dashboard page."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

import database
from launchpad.scoring import fmt_thirtieth, normalize_outcome, ui_outcome_copy
from launchpad.ui.components import (
    admin_badge_html,
    admin_progress_html,
    admin_quota_html,
    admin_rank_html,
)


def page_admin(sb: Any, profile: dict[str, Any]) -> None:
    if not profile.get("is_admin"):
        st.error("Accesso negato.")
        return
    st.header("Admin")
    profiles = database.admin_list_profiles()
    ideas = database.admin_list_ideas()
    st.caption("Numeri globali, leaderboard e gestione utenti.")

    _render_global_stats(profiles, ideas)
    _render_hall_of_fame()
    _render_user_management(sb, profiles)
    _render_ideas_archive(ideas)


def _render_global_stats(profiles: list[dict[str, Any]], ideas: list[dict[str, Any]]) -> None:
    validated_ideas = [idea for idea in ideas if idea.get("status") == "validated"]
    not_now_count = sum(
        1 for idea in validated_ideas if normalize_outcome(str(idea.get("yc_verdict") or "")) == "NOT NOW"
    )
    destruction_rate = (not_now_count / len(validated_ideas) * 100) if validated_ideas else 0.0
    approved_users = sum(1 for user in profiles if user.get("is_approved"))
    active_users = sum(1 for user in profiles if int(user.get("ideas_this_week") or 0) > 0)
    pending_users = sum(1 for user in profiles if not user.get("is_approved"))

    with st.container(border=True):
        st.markdown("<div class='admin-section-kicker'>Global Stats</div>", unsafe_allow_html=True)
        stat_cols = st.columns(3)
        stat_cols[0].metric("Total Ideas", len(ideas), delta=f"{len(validated_ideas)} validated")
        stat_cols[1].metric("Destruction Rate", f"{destruction_rate:.0f}%", delta=f"{not_now_count} NOT NOW")
        stat_cols[2].metric("Active Users", active_users, delta=f"{approved_users} approved")
        if pending_users:
            st.caption(f"{pending_users} utenti in attesa di approvazione.")


def _render_hall_of_fame() -> None:
    st.subheader("Hall of Fame")
    st.caption("Wall of Genius con ranking, score visuale e verdetto a badge.")
    try:
        hall_of_fame = database.admin_hall_of_fame()
    except Exception as e:  # noqa: BLE001
        st.warning(
            "Hall of Fame non disponibile: probabilmente non hai ancora applicato la migrazione DB v2.5 "
            "(colonne scoring idea: `vision_score`, `dependency_score`, `real_feasibility`, ecc.)."
        )
        st.code(str(e))
        hall_of_fame = []
    if not hall_of_fame:
        st.markdown("<div class='admin-empty'>Nessuna idea validata con punteggio ancora.</div>", unsafe_allow_html=True)
        return

    for idx, item in enumerate(hall_of_fame, start=1):
        title = item.get("title") or "Senza titolo"
        vision_score = item.get("vision_score")
        feasibility_score = item.get("feasibility_score")
        dependency_score = item.get("dependency_score")
        real_feasibility = item.get("real_feasibility")
        final_score = item.get("final_score")
        verdict_title, verdict_hint, verdict_color = ui_outcome_copy(str(item.get("yc_verdict") or ""))
        author_email = item.get("author_email") or "—"
        with st.container(border=True):
            rank_col, info_col, score_col, verdict_col = st.columns((1.1, 4.3, 2.9, 2.1))
            with rank_col:
                st.markdown(admin_rank_html(idx), unsafe_allow_html=True)
            with info_col:
                stats_html = "".join(
                    [
                        f"<span class='admin-mini-pill admin-mono'>V {fmt_thirtieth(vision_score)}</span>",
                        f"<span class='admin-mini-pill admin-mono'>F {fmt_thirtieth(feasibility_score)}</span>",
                        f"<span class='admin-mini-pill admin-mono'>D {fmt_thirtieth(dependency_score)}</span>",
                        f"<span class='admin-mini-pill admin-mono'>RF {fmt_thirtieth(real_feasibility)}</span>",
                    ]
                )
                st.markdown(
                    (
                        f"<div class='admin-card-title'>{html.escape(str(title))}</div>"
                        f"<div class='admin-card-subtitle'>{html.escape(str(author_email))}</div>"
                        f"<div>{stats_html}</div>"
                    ),
                    unsafe_allow_html=True,
                )
            with score_col:
                st.markdown(admin_progress_html(final_score), unsafe_allow_html=True)
            with verdict_col:
                st.markdown(
                    admin_badge_html(verdict_title, verdict_color)
                    + f"<div class='admin-microcopy'>{html.escape(verdict_hint)}</div>",
                    unsafe_allow_html=True,
                )


def _render_user_management(sb: Any, profiles: list[dict[str, Any]]) -> None:
    st.subheader("User Management")
    st.caption("Card responsive con stato, quota e azioni rapide.")
    for profile in profiles:
        user_email = profile.get("email") or profile["id"]
        ideas_this_week = int(profile.get("ideas_this_week") or 0)
        weekly_limit = int(profile.get("weekly_ideas_limit") or 3)
        status_badges = [
            admin_badge_html(
                "APPROVED" if profile.get("is_approved") else "PENDING",
                "#0F766E" if profile.get("is_approved") else "#64748B",
            )
        ]
        if profile.get("is_admin"):
            status_badges.append(admin_badge_html("ADMIN", "#1D4ED8"))
        with st.container(border=True):
            info_col, quota_col = st.columns((4, 2.1))
            with info_col:
                st.markdown(
                    (
                        f"<div class='admin-card-title'>{html.escape(str(user_email))}</div>"
                        f"<div class='admin-card-subtitle admin-mono'>{html.escape(str(profile['id']))}</div>"
                        f"<div>{''.join(status_badges)}</div>"
                    ),
                    unsafe_allow_html=True,
                )
            with quota_col:
                st.markdown(admin_quota_html(ideas_this_week, weekly_limit), unsafe_allow_html=True)

            action_cols = st.columns(3)
            approve_label = "🚫 Revoca" if profile.get("is_approved") else "✅ Approva"
            admin_label = "🛡️ Rimuovi Admin" if profile.get("is_admin") else "🛡️ Rendi Admin"
            if action_cols[0].button(approve_label, key=f"ap_{profile['id']}", use_container_width=True):
                database.admin_set_approved(profile["id"], not profile.get("is_approved"))
                st.rerun()
            if action_cols[1].button(admin_label, key=f"ad_{profile['id']}", use_container_width=True):
                database.admin_set_admin(profile["id"], not profile.get("is_admin"))
                st.rerun()
            if action_cols[2].button("♻️ Reset Quota", key=f"rq_{profile['id']}", use_container_width=True):
                try:
                    database.admin_reset_ideas_this_week(sb, str(profile["id"]))
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(str(e))


def _render_ideas_archive(ideas: list[dict[str, Any]]) -> None:
    with st.expander("Archivio completo idee"):
        for idea in ideas:
            with st.container(border=True):
                admin_outcome = ui_outcome_copy(str(idea.get("yc_verdict") or ""))[0]
                st.markdown(
                    (
                        f"<div class='admin-card-title'>{html.escape(str(idea.get('title') or 'Senza titolo'))}</div>"
                        f"<div class='admin-card-subtitle admin-mono'>{html.escape(str(idea['id']))}</div>"
                    ),
                    unsafe_allow_html=True,
                )
                st.write(
                    f"user_id: `{idea.get('user_id')}` · status: `{idea.get('status')}` · "
                    f"esito: `{admin_outcome}` · "
                    f"vision: `{fmt_thirtieth(idea.get('vision_score'))}` · "
                    f"dependency: `{fmt_thirtieth(idea.get('dependency_score'))}` · "
                    f"real_feasibility: `{fmt_thirtieth(idea.get('real_feasibility'))}`"
                )
                if idea.get("structured_data"):
                    st.json(idea["structured_data"])
                if idea.get("analysis_report"):
                    st.markdown(idea["analysis_report"])

