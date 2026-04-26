"""Score formatting and Launchpad verdict helpers."""

from __future__ import annotations

from typing import Any

import ai_engine


def score_color(score: int) -> str:
    if score <= 39:
        return "#f59e0b"
    if score <= 69:
        return "#f6c343"
    return "#2e8b57"


def to_thirtieth(score: float | int | None) -> float:
    raw = 0.0 if score is None else float(score)
    clamped = max(0.0, min(100.0, raw))
    return round(clamped * 0.3, 1)


def fmt_thirtieth(score: float | int | None) -> str:
    value = to_thirtieth(score)
    if float(value).is_integer():
        return f"{int(value)}/30"
    return f"{value:.1f}/30"


def normalize_outcome(verdict: str) -> str:
    value = str(verdict or "").strip().upper()
    if value == "BUILD":
        return "GO"
    if value == "ITERATE":
        return "PIVOT"
    if value in {"GO", "PIVOT", "CAUTION", "NOT NOW"}:
        return value
    return "NOT NOW"


def ui_outcome_copy(verdict: str) -> tuple[str, str, str]:
    value = normalize_outcome(verdict)
    if value == "GO":
        return "GO", "Lancio consigliato", "#50C878"
    if value == "PIVOT":
        return "PIVOT", "Idea valida, esecuzione da rivedere", "#FFD700"
    if value == "CAUTION":
        return "CAUTION", "Costruibile, ma molti vincoli", "#FF7F00"
    return "NOT NOW", "Poche chance di successo ora", "#DC143C"


def compute_row_decision(row: dict[str, Any]) -> dict[str, float | int | str]:
    vision = int(row.get("vision_score") or 0)
    feasibility = int(row.get("feasibility_score") or 0)
    dependency_raw = row.get("dependency_score")
    dependency = 50 if dependency_raw is None else int(dependency_raw)
    computed = ai_engine.compute_yc_decision(vision, feasibility, dependency)
    computed["yc_verdict"] = normalize_outcome(str(computed.get("yc_verdict") or ""))
    return computed


def legacy_storage_outcome(verdict: str) -> str:
    value = normalize_outcome(verdict)
    if value == "GO":
        return "BUILD"
    if value in {"PIVOT", "CAUTION"}:
        return "ITERATE"
    return "NOT NOW"

