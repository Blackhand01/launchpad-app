"""Gemini-first blueprint (fallback Groq), Groq audio transcription, OpenAI GPT-5 validation."""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import google.generativeai as genai
from groq import Groq
from openai import OpenAI

_PHASE_MESSAGES = (
    "Checking the laws of physics...",
    "Investigating if Big Tech will block us...",
    "Consulting the crystal ball (and Google)...",
)

VALIDATOR_SYSTEM_PROMPT = """Sei un mentore pragmatico e concreto. Parla SOLO in italiano colloquiale, senza jargon startup.

Usa la ricerca web quando utile per verificare limiti tecnici, API, policy e vincoli reali.

OBIETTIVO:
Valutare se il prodotto è costruibile davvero oggi da un team piccolo, non solo se la tecnologia esiste.
Non devi "stroncare" l'idea: devi spiegare come renderla testabile e lanciabile in modo progressivo.

SCORING:
- vision_score (0-100): potenziale lungo termine.
- feasibility_score (0-100): costruibilità immediata da team piccolo.
- dependency_score (0-100): rischio di dipendenza da terze parti.
  0 = totalmente indipendente.
  100 = totalmente dipendente da altri.

DEPENDENCY INCLUDE:
- infrastruttura fisica non controllata dal team
- API private / entitlement / accessi privilegiati
- accordi commerciali obbligatori
- hardware posseduto da terzi
- gatekeeper piattaforma (Apple, Google, vendor enterprise)

REGOLA FONDAMENTALE:
Non confondere "la tecnologia esiste" con "il prodotto è lanciabile dal team".
Do NOT treat existing solutions as proof of feasibility unless the team can build them without permission.

VALUTAZIONE COSTRUTTIVA:
- Se ci sono blocchi esterni, penalizza ma proponi una versione MVP che possa partire senza quei blocchi.
- Se il percorso è lento, descrivi il primo esperimento utile in 7 giorni.
- Evita giudizi assoluti senza piano di rilancio pratico.

SPEED CHECK (OBBLIGATORIO):
Nel reasoning aggiungi SEMPRE sezione "## Speed Check" e valuta:
- Può essere testato in < 7 giorni?
- Il primo utente riceve valore subito?
- Richiede deployment/integrazione lunga?
Se è lento, riduci feasibility_score in modo proporzionato e spiega perché.

OUTPUT:
Restituisci SOLO JSON valido con chiavi esatte:
{
"vision_score": int (0-100),
"feasibility_score": int (0-100),
"dependency_score": int (0-100),
"yc_verdict": "BUILD" | "ITERATE" | "NOT NOW",
"reasoning": stringa con sezioni:
  "## Physics Check"
  "## Control Check"
  "## Speed Check",
"pivot_suggestion": stringa con versione costruibile in ~14 giorni
}
"""


def _openai() -> OpenAI:
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _gemini_configure() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: GEMINI_API_KEY")
    genai.configure(api_key=api_key)


def _gemini_blueprint_model() -> str:
    return os.getenv("GEMINI_BLUEPRINT_MODEL", "gemini-2.5-flash")


def _groq() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing required environment variable: GROQ_API_KEY")
    return Groq(api_key=api_key)


def _is_decommissioned_model_error(err: Exception) -> bool:
    msg = str(err).lower()
    return "model_decommissioned" in msg or "decommissioned" in msg


def _is_gemini_quota_error(err: Exception) -> bool:
    msg = str(err).lower()
    return (
        "resource_exhausted" in msg
        or "resource exhausted" in msg
        or "quota" in msg
        or "429" in msg
        or "rate limit" in msg
    )


def _is_gemini_unavailable_error(err: Exception) -> bool:
    msg = str(err).lower()
    return "missing required environment variable: gemini_api_key" in msg


def _blueprint_model_candidates() -> list[str]:
    primary = (os.getenv("GROQ_BLUEPRINT_MODEL") or "openai/gpt-oss-120b").strip()
    fallback_raw = os.getenv("GROQ_BLUEPRINT_FALLBACK_MODELS") or "llama-3.3-70b-versatile,llama-3.1-8b-instant"
    candidates: list[str] = [primary]
    candidates.extend([m.strip() for m in fallback_raw.split(",") if m.strip()])
    deduped: list[str] = []
    for model in candidates:
        if model not in deduped:
            deduped.append(model)
    return deduped


def get_blueprint_model_candidates() -> list[str]:
    """Public helper for UI/debug visibility of the model chain."""
    models: list[str] = []
    gemini_model = _gemini_blueprint_model()
    if gemini_model:
        models.append(gemini_model)
    models.extend(_blueprint_model_candidates())
    deduped: list[str] = []
    for model in models:
        if model not in deduped:
            deduped.append(model)
    return deduped


def transcribe_audio_streamlit_file(uploaded_file) -> str:
    """Transcribe user audio using Groq Whisper."""
    client = _groq()
    model_name = os.getenv("GROQ_TRANSCRIPTION_MODEL", "whisper-large-v3")
    file_name = getattr(uploaded_file, "name", "") or "audio.wav"
    audio_bytes = uploaded_file.getvalue()
    if not audio_bytes:
        raise RuntimeError("Audio vuoto: impossibile trascrivere.")
    transcription = client.audio.transcriptions.create(
        file=(file_name, audio_bytes),
        model=model_name,
        response_format="text",
        language="it",
    )
    text = str(transcription or "").strip()
    if not text:
        raise RuntimeError("Trascrizione vuota dal modello.")
    return text


def build_product_blueprint(raw_transcript: str) -> dict[str, Any]:
    """Phase 1: convert raw input into ordered blueprint without adding new information."""
    system = (
        "Trasforma l'input in un blueprint ordinato SENZA aggiungere informazioni. "
        "Regole obbligatorie: usa solo contenuti espliciti presenti nel testo input; "
        "non inferire, non completare, non inventare dettagli; se un campo manca, lascialo vuoto. "
        "Mantieni il significato originale, puoi solo riorganizzare/compattare frasi già presenti. "
        "Rispondi SOLO con JSON valido con chiavi esatte: problem, solution, key_features. "
        "key_features deve essere array di stringhe."
    )
    user = (
        "Input grezzo:\n"
        f"{raw_transcript}\n\n"
        "Ordina l'idea in blueprint rispettando le regole senza aggiungere nulla."
    )

    # 1) Gemini first
    gemini_model = _gemini_blueprint_model()
    try:
        _gemini_configure()
        g_model = genai.GenerativeModel(
            gemini_model,
            system_instruction=system,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        g_resp = g_model.generate_content(user)
        g_raw = (g_resp.text or "").strip() or "{}"
        data = _extract_json_object(g_raw)
        used_model = gemini_model
    except Exception as gemini_err:
        if not (_is_gemini_quota_error(gemini_err) or _is_gemini_unavailable_error(gemini_err)):
            raise

        # 2) Fallback to Groq only when Gemini quota is exhausted
        client = _groq()
        last_err: Exception | None = None
        used_model: str | None = None
        raw = "{}"
        for model_name in _blueprint_model_candidates():
            try:
                try:
                    completion = client.chat.completions.create(
                        model=model_name,
                        temperature=0.1,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        response_format={"type": "json_object"},
                    )
                except Exception as e:
                    if _is_decommissioned_model_error(e):
                        last_err = e
                        continue
                    # Some Groq model configs may reject response_format; retry with prompt-only JSON constraint.
                    completion = client.chat.completions.create(
                        model=model_name,
                        temperature=0.1,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    )
                raw = completion.choices[0].message.content or "{}"
                used_model = model_name
                break
            except Exception as e:
                if _is_decommissioned_model_error(e):
                    last_err = e
                    continue
                raise

        if not used_model:
            if last_err is not None:
                raise RuntimeError(
                    "Gemini quota esaurita e i modelli blueprint Groq configurati risultano decommissionati/non disponibili. "
                    "Aggiorna GROQ_BLUEPRINT_MODEL / GROQ_BLUEPRINT_FALLBACK_MODELS."
                ) from last_err
            raise RuntimeError("Gemini quota esaurita e nessun modello blueprint Groq disponibile.")

        data = _extract_json_object(raw)

    kf = data.get("key_features") or []
    if not isinstance(kf, list):
        kf = [str(kf)]
    return {
        "problem": str(data.get("problem", "")).strip(),
        "solution": str(data.get("solution", "")).strip(),
        "key_features": [str(x).strip() for x in kf if str(x).strip()],
        "_model_used": used_model,
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.I)
        t = re.sub(r"\s*```\s*$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        # Fallback: model occasionally wraps JSON with extra prose despite strict prompting.
        m = re.search(r"\{.*\}", t, flags=re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def _coerce_validation_json(
    raw_text: str,
    *,
    client: OpenAI,
    source_model: str,
) -> tuple[dict[str, Any], bool]:
    """Parse validation JSON; if malformed, ask a model to repair structure only."""
    try:
        return _extract_json_object(raw_text), False
    except json.JSONDecodeError as first_err:
        repair_model = os.getenv("OPENAI_JSON_REPAIR_MODEL", source_model)
        repair_system = (
            "Converti il testo ricevuto in JSON valido. "
            "Non aggiungere nuove informazioni fattuali. "
            "Mantieni SOLO queste chiavi: vision_score, feasibility_score, dependency_score, yc_verdict, reasoning, pivot_suggestion. "
            "Restituisci SOLO JSON valido."
        )
        repair_user = (
            "Testo da riparare (potrebbe contenere quasi-JSON non valido):\n"
            f"{raw_text[:30000]}"
        )
        try:
            repair_resp = client.chat.completions.create(
                model=repair_model,
                response_format={"type": "json_object"},
                temperature=0,
                messages=[
                    {"role": "system", "content": repair_system},
                    {"role": "user", "content": repair_user},
                ],
            )
            repaired_raw = repair_resp.choices[0].message.content or "{}"
            return _extract_json_object(repaired_raw), True
        except Exception as repair_err:  # noqa: BLE001
            raise RuntimeError(
                f"Validazione: JSON non valido dal modello e repair fallito. Parse error: {first_err}"
            ) from repair_err


def _force_validation_json_generation(
    *,
    client: OpenAI,
    model: str,
    blueprint_text: str,
) -> str:
    """Last LLM rescue path when Responses API returns empty/non-parseable output."""
    rescue_system = (
        VALIDATOR_SYSTEM_PROMPT
        + "\n\nRegola extra: rispondi con SOLO JSON valido, senza testo extra, markdown o backticks."
    )
    rescue_user = (
        "Blueprint prodotto:\n"
        f"{blueprint_text}\n\n"
        "Genera ora il JSON richiesto."
    )

    # Prefer chat.completions JSON mode for strictness.
    try:
        completion = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": rescue_system},
                {"role": "user", "content": rescue_user},
            ],
        )
        raw = completion.choices[0].message.content or ""
        if raw.strip():
            return raw
    except Exception:
        pass

    # Secondary rescue via Responses API without tools.
    try:
        resp = client.responses.create(
            model=model,
            instructions=rescue_system,
            input=rescue_user,
            max_output_tokens=1200,
        )
        return _responses_output_text(resp) or ""
    except Exception:
        return ""


def _safe_validation_fallback(blueprint: dict[str, Any]) -> dict[str, Any]:
    """Deterministic fallback to avoid hard failure when model output is unrecoverable."""
    text_blob = (
        f"{blueprint.get('problem', '')}\n{blueprint.get('solution', '')}\n"
        + "\n".join(str(x) for x in (blueprint.get("key_features") or []))
    ).lower()
    dependency = 50
    if any(k in text_blob for k in ("ble", "hardware", "skipass", "entitlement", "api private", "accordi")):
        dependency = 75
    feasibility = 60 if dependency <= 50 else 35
    vision = 65
    decision = compute_yc_decision(vision, feasibility, dependency)
    reasoning = (
        "## Physics Check\n"
        "Fallback automatico: non è stato possibile ottenere JSON valido dal modello.\n\n"
        "## Control Check\n"
        "Valutazione prudente applicata in base al testo del blueprint e alla dipendenza stimata.\n\n"
        "## Speed Check\n"
        "Assunto scenario medio: se servono integrazioni esterne la fattibilità viene ridotta, "
        "ma resta suggerito un test MVP standalone."
    )
    return {
        "vision_score": vision,
        "feasibility_score": feasibility,
        "dependency_score": dependency,
        "yc_verdict": str(decision["yc_verdict"]),
        "reasoning": reasoning,
        "pivot_suggestion": "Costruisci una MVP standalone in 14 giorni senza integrazioni bloccanti.",
    }


def _parse_check_sections(reasoning: str) -> tuple[str, str, str]:
    phys = ""
    ctrl = ""
    speed = ""
    m_p = re.search(
        r"##\s*Physics Check\s*(.+?)(?=##\s*Control Check\b|##\s*Speed Check\b|\Z)",
        reasoning,
        flags=re.S | re.I,
    )
    m_c = re.search(
        r"##\s*Control Check\s*(.+?)(?=##\s*Speed Check\b|\Z)",
        reasoning,
        flags=re.S | re.I,
    )
    m_s = re.search(r"##\s*Speed Check\s*(.+)", reasoning, flags=re.S | re.I)
    if m_p:
        phys = re.sub(r"\s+", " ", m_p.group(1).strip())
    if m_c:
        ctrl = re.sub(r"\s+", " ", m_c.group(1).strip())
    if m_s:
        speed = re.sub(r"\s+", " ", m_s.group(1).strip())
    return phys[:800], ctrl[:800], speed[:800]


def _urls_in_text(text: str) -> list[dict[str, str]]:
    urls = re.findall(r"https?://[^\s\)\]\"']+", text)
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append({"url": u})
    return out[:25]


def _yc_verdict_from_scores(real_feasibility: float, final_score: float) -> str:
    if final_score >= 70 and real_feasibility >= 50:
        return "BUILD"
    if final_score >= 45 or real_feasibility >= 38:
        return "ITERATE"
    return "NOT NOW"


def _clamp_0_100(value: int) -> int:
    return max(0, min(100, int(value)))


def compute_yc_decision(
    vision_score: int,
    feasibility_score: int,
    dependency_score: int | None,
) -> dict[str, float | int | str]:
    """Deterministic scoring tuned for coaching and actionability in Launchpad."""
    vision = _clamp_0_100(vision_score)
    feasibility = _clamp_0_100(feasibility_score)
    dependency = 50 if dependency_score is None else _clamp_0_100(dependency_score)
    dependency_penalty = round(dependency * 0.30, 1)
    vision_bonus = round(max(0.0, (vision - 55) * 0.15), 1)
    real_feasibility = round(max(0.0, min(100.0, feasibility - dependency_penalty + vision_bonus)), 1)
    final_score = round(max(0.0, min(100.0, (real_feasibility * 0.6) + (vision * 0.4))), 1)
    yc_verdict = _yc_verdict_from_scores(real_feasibility, final_score)
    return {
        "vision_score": vision,
        "feasibility_score": feasibility,
        "dependency_score": dependency,
        "dependency_penalty": dependency_penalty,
        "vision_bonus": vision_bonus,
        "real_feasibility": real_feasibility,
        "final_score": final_score,
        "yc_verdict": yc_verdict,
    }


def run_feasibility_validation(
    blueprint: dict[str, Any],
    *,
    status_writer: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """
    Phase 2: web-backed validation. Returns dict with scoring fields.
    """
    client = _openai()
    model = os.getenv("OPENAI_VALIDATION_MODEL", "gpt-5")
    http_timeout_s = float(os.getenv("OPENAI_VALIDATION_HTTP_TIMEOUT_SECONDS", "120"))
    stream_max_s = float(os.getenv("OPENAI_VALIDATION_STREAM_MAX_SECONDS", "90"))
    started = datetime.now(timezone.utc).isoformat()
    timeline: list[dict[str, str]] = [{"ts": started, "event": "validation_started"}]

    blueprint_text = json.dumps(blueprint, ensure_ascii=False, indent=2)
    user_prompt = (
        "Valuta il seguente blueprint prodotto.\n\n"
        f"{blueprint_text}\n\n"
        "Usa la ricerca web dove serve. Restituisci SOLO il JSON richiesto dalle istruzioni di sistema."
    )

    msg_idx = 0
    sent_msgs: list[str] = []

    def phase_msg() -> None:
        nonlocal msg_idx
        if status_writer:
            msg = _PHASE_MESSAGES[msg_idx % len(_PHASE_MESSAGES)]
            status_writer(msg)
            sent_msgs.append(msg)
            msg_idx += 1

    if status_writer:
        phase_msg()

    req_client = client.with_options(timeout=http_timeout_s)
    final_text_parts: list[str] = []
    stream = req_client.responses.create(
        model=model,
        tools=[{"type": "web_search"}],
        tool_choice="auto",
        instructions=VALIDATOR_SYSTEM_PROMPT,
        input=user_prompt,
        stream=True,
    )
    started_monotonic = time.monotonic()
    last_status_at = 0.0
    for event in stream:
        elapsed = time.monotonic() - started_monotonic
        if elapsed > stream_max_s:
            now = datetime.now(timezone.utc).isoformat()
            timeline.append({"ts": now, "event": "response.stream_timeout_break"})
            if status_writer:
                status_writer("Timeout ricerca web: passo al fallback rapido.")
            close_fn = getattr(stream, "close", None)
            if callable(close_fn):
                close_fn()
            break

        et = getattr(event, "type", "") or ""
        if et == "response.output_text.delta":
            final_text_parts.append(event.delta)
        elif et.startswith("response.web_search_call"):
            now = datetime.now(timezone.utc).isoformat()
            timeline.append({"ts": now, "event": et})
            if (
                status_writer
                and et in (
                    "response.web_search_call.searching",
                    "response.web_search_call.in_progress",
                    "response.web_search_call.completed",
                )
                and (elapsed - last_status_at) >= 2.0
            ):
                phase_msg()
                last_status_at = elapsed
        elif et == "response.completed":
            now = datetime.now(timezone.utc).isoformat()
            timeline.append({"ts": now, "event": et})

    raw = "".join(final_text_parts).strip()
    if not raw:
        if status_writer:
            phase_msg()
        resp = req_client.responses.create(
            model=model,
            tools=[{"type": "web_search"}],
            tool_choice="auto",
            instructions=VALIDATOR_SYSTEM_PROMPT,
            input=user_prompt,
            max_output_tokens=1200,
        )
        raw = _responses_output_text(resp) or ""
    if not raw:
        # Last-resort fast fallback without web_search to avoid indefinite waits.
        if status_writer:
            status_writer("Fallback finale senza ricerca web.")
        resp = req_client.responses.create(
            model=model,
            instructions=VALIDATOR_SYSTEM_PROMPT,
            input=user_prompt,
            max_output_tokens=1200,
        )
        raw = _responses_output_text(resp) or ""
    if not raw:
        if status_writer:
            status_writer("Recovery JSON dedicato.")
        raw = _force_validation_json_generation(
            client=client,
            model=model,
            blueprint_text=blueprint_text,
        )

    completed = datetime.now(timezone.utc).isoformat()
    timeline.append({"ts": completed, "event": "validation_completed"})

    if status_writer:
        # Guarantee all required UX loading messages appear at least once.
        for msg in _PHASE_MESSAGES:
            if msg not in sent_msgs:
                status_writer(msg)

    used_safe_fallback = False
    if not raw.strip():
        data = _safe_validation_fallback(blueprint)
        was_repaired = False
        used_safe_fallback = True
    else:
        try:
            data, was_repaired = _coerce_validation_json(raw, client=client, source_model=model)
        except RuntimeError:
            data = _safe_validation_fallback(blueprint)
            was_repaired = False
            used_safe_fallback = True

    decision = compute_yc_decision(
        int(data.get("vision_score", 0)),
        int(data.get("feasibility_score", 0)),
        data.get("dependency_score"),
    )
    vision = int(decision["vision_score"])
    feasibility = int(decision["feasibility_score"])
    dependency = int(decision["dependency_score"])
    dependency_penalty = float(decision["dependency_penalty"])
    vision_bonus = float(decision["vision_bonus"])
    real_feasibility = float(decision["real_feasibility"])
    final_score = float(decision["final_score"])
    yc_verdict = str(decision["yc_verdict"])

    reasoning = str(data.get("reasoning") or data.get("sandwich_report") or "").strip()
    pivot = str(data.get("pivot_suggestion", "")).strip()
    if not reasoning:
        raise RuntimeError("Validazione: reasoning vuoto.")
    phys_summary, ctrl_summary, speed_summary = _parse_check_sections(reasoning)
    sources = _urls_in_text(reasoning + "\n" + raw)
    model_yc_verdict = str(data.get("yc_verdict", "")).strip().upper()

    thought_log: dict[str, Any] = {
        "run": {
            "model": model,
            "started_at": started,
            "completed_at": completed,
            "json_repaired": was_repaired,
            "safe_fallback_used": used_safe_fallback,
        },
        "check_summaries": {
            "physics_check": phys_summary,
            "control_check": ctrl_summary,
            "speed_check": speed_summary,
        },
        "source_links": sources,
        "raw_scores": {
            "vision_score": vision,
            "feasibility_score": feasibility,
            "dependency_score": dependency,
        },
        "adjusted_scores": {
            "dependency_penalty": dependency_penalty,
            "vision_bonus": vision_bonus,
            "real_feasibility": real_feasibility,
            "final_score": final_score,
        },
        "verdicts": {
            "yc_verdict": yc_verdict,
            "model_yc_verdict": model_yc_verdict,
            "model_verdict_matches_engine": model_yc_verdict == yc_verdict if model_yc_verdict else None,
        },
        "blueprint_snapshot": blueprint,
        "timeline": timeline[-40:],
    }

    return {
        "vision_score": vision,
        "feasibility_score": feasibility,
        "dependency_score": dependency,
        "real_feasibility": real_feasibility,
        "final_score": final_score,
        "yc_verdict": yc_verdict,
        "reasoning": reasoning,
        "sandwich_report": reasoning,  # backward compatibility for existing UI calls
        "pivot_suggestion": pivot,
        "thought_log": thought_log,
    }


def _responses_output_text(resp: Any) -> str:
    out = getattr(resp, "output_text", None)
    if isinstance(out, str) and out.strip():
        return out.strip()
    output = getattr(resp, "output", None) or []
    chunks: list[str] = []
    for item in output:
        if getattr(item, "type", None) == "message":
            content = getattr(item, "content", None) or []
            for c in content:
                t = getattr(c, "text", None)
                if t:
                    chunks.append(t)
    return "\n".join(chunks).strip()
