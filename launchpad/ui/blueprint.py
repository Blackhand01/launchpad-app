"""Reusable blueprint editing controls."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_blueprint_editor(
    idea_id: str,
    structured_data: dict[str, Any],
    *,
    key_prefix: str,
) -> dict[str, Any]:
    problem = st.text_area(
        "Problem",
        value=structured_data.get("problem", ""),
        height=100,
        key=f"{key_prefix}_problem_{idea_id}",
    )
    solution = st.text_area(
        "Solution",
        value=structured_data.get("solution", ""),
        height=100,
        key=f"{key_prefix}_solution_{idea_id}",
    )
    key_features = structured_data.get("key_features") or []
    features_text = st.text_area(
        "Key features (una per riga)",
        value="\n".join(str(x) for x in key_features),
        height=120,
        key=f"{key_prefix}_kf_{idea_id}",
    )
    feature_lines = [line.strip() for line in features_text.splitlines() if line.strip()]
    return {
        "problem": problem,
        "solution": solution,
        "key_features": feature_lines,
    }

