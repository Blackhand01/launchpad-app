from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from dotenv import load_dotenv


@dataclass(frozen=True)
class BatteryCase:
    index: int
    name: str
    raw_input: str
    expected_verdict_raw: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


load_dotenv(_repo_root() / ".env")
sys.path.insert(0, str(_repo_root()))
import ai_engine  # noqa: E402


def _battery_md_path() -> Path:
    return _repo_root() / "docs" / "test.md"


def _parse_battery_cases(path: Path) -> list[BatteryCase]:
    text = path.read_text(encoding="utf-8")
    header_re = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$", re.M)
    headers = list(header_re.finditer(text))
    cases: list[BatteryCase] = []

    for i, match in enumerate(headers):
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        chunk = text[start:end]

        raw_match = re.search(r"```text\s*(.*?)\s*```", chunk, flags=re.S | re.I)
        verdict_match = re.search(r"\*\s*Verdict:\s*(.+)", chunk)
        if not raw_match or not verdict_match:
            continue

        cases.append(
            BatteryCase(
                index=int(match.group(1)),
                name=match.group(2).strip(),
                raw_input=raw_match.group(1).strip(),
                expected_verdict_raw=verdict_match.group(1).strip(),
            )
        )

    return cases


def _expected_verdict_set(raw: str) -> set[str]:
    label = raw.upper()
    expected: set[str] = set()
    if "BUILD" in label:
        expected.add("BUILD")
    if "NOT NOW" in label:
        expected.add("NOT NOW")
    if "ITERATE" in label:
        expected.add("ITERATE")
    return expected


def _yc_verdict_from_feasibility(feasibility_score: int) -> str:
    if feasibility_score >= 70:
        return "BUILD"
    if feasibility_score >= 40:
        return "ITERATE"
    return "NOT NOW"


def _to_blueprint(raw_input: str) -> dict[str, object]:
    # Keep conversion deterministic and lightweight: we test Phase 2 validator only.
    return {
        "problem": raw_input,
        "solution": raw_input,
        "key_features": [],
    }


def _render_table(rows: list[dict[str, str]]) -> str:
    headers = ["#", "Idea", "Expected", "Predicted", "Vision", "Feas", "Legacy", "Match"]
    str_rows = [
        [
            row["index"],
            row["idea"],
            row["expected"],
            row["predicted"],
            row["vision"],
            row["feasibility"],
            row["legacy"],
            row["match"],
        ]
        for row in rows
    ]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def _line(cells: list[str]) -> str:
        return " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    sep = "-+-".join("-" * w for w in widths)
    lines = [_line(headers), sep]
    lines.extend(_line(row) for row in str_rows)
    return "\n".join(lines)


def test_validator_battery_report() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY non impostata: test integrazione validator saltato.")

    cases = _parse_battery_cases(_battery_md_path())
    assert cases, "Nessun caso trovato in docs/test.md"

    limit_raw = os.getenv("VALIDATOR_BATTERY_LIMIT", "").strip()
    if limit_raw:
        cases = cases[: int(limit_raw)]

    rows: list[dict[str, str]] = []
    mismatches: list[str] = []

    for case in cases:
        result = ai_engine.run_feasibility_validation(_to_blueprint(case.raw_input))
        vision = int(result["vision_score"])
        feasibility = int(result["feasibility_score"])
        predicted = _yc_verdict_from_feasibility(feasibility)
        expected_set = _expected_verdict_set(case.expected_verdict_raw)
        is_match = predicted in expected_set if expected_set else False

        if not is_match:
            mismatches.append(
                f"{case.index}. {case.name}: expected={case.expected_verdict_raw}, got={predicted}"
            )

        rows.append(
            {
                "index": str(case.index),
                "idea": case.name,
                "expected": case.expected_verdict_raw,
                "predicted": predicted,
                "vision": str(vision),
                "feasibility": str(feasibility),
                "legacy": str(result.get("verdict", "")),
                "match": "OK" if is_match else "MISS",
            }
        )

    print("\nValidator battery results:\n")
    print(_render_table(rows))

    strict_mode = os.getenv("VALIDATOR_BATTERY_STRICT", "0") == "1"
    if strict_mode and mismatches:
        pytest.fail("Mismatches found:\n- " + "\n- ".join(mismatches))
