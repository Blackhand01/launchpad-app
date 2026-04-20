"""Supabase CRUD and clients. User-scoped operations use the anon key + session."""

from __future__ import annotations

import os
from typing import Any

from supabase import Client, create_client


class WeeklyQuotaReachedError(Exception):
    """Raised when create_idea_with_quota hits the user's weekly limit."""


class MissingRpcError(Exception):
    """Raised when required Supabase RPCs are not deployed/visible yet."""


def _require(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


def anon_supabase() -> Client:
    return create_client(_require("SUPABASE_URL"), _require("SUPABASE_ANON_KEY"))


def service_supabase() -> Client:
    return create_client(_require("SUPABASE_URL"), _require("SUPABASE_SERVICE_ROLE_KEY"))


def user_client(access_token: str, refresh_token: str) -> Client:
    client = anon_supabase()
    client.auth.set_session(access_token, refresh_token)
    return client


def fetch_profile(client: Client, user_id: str) -> dict[str, Any] | None:
    res = client.table("profiles").select("*").eq("id", user_id).single().execute()
    return res.data


def list_my_ideas(client: Client, user_id: str) -> list[dict[str, Any]]:
    res = (
        client.table("ideas")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def get_idea(client: Client, idea_id: str, user_id: str) -> dict[str, Any] | None:
    res = (
        client.table("ideas")
        .select("*")
        .eq("id", idea_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return res.data


def create_idea(
    client: Client,
    user_id: str,
    *,
    title: str,
    raw_transcript: str | None = None,
    status: str = "raw",
) -> dict[str, Any]:
    """Direct insert (no quota). Prefer create_idea_with_quota from the app."""
    payload = {
        "user_id": user_id,
        "title": title,
        "raw_transcript": raw_transcript,
        "status": status,
    }
    res = client.table("ideas").insert(payload).execute()
    return res.data[0] if res.data else {}


def create_idea_with_quota(
    client: Client,
    *,
    title: str,
    raw_transcript: str | None = None,
    status: str = "raw",
) -> dict[str, Any]:
    """Atomic quota check + increment + idea insert (Supabase RPC)."""
    try:
        res = client.rpc(
            "create_idea_with_quota",
            {"title": title, "raw_transcript": raw_transcript or "", "status": status},
        ).execute()
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "PGRST202" in msg and "create_idea_with_quota" in msg:
            raise MissingRpcError(
                "Missing Supabase RPC `public.create_idea_with_quota(title text, raw_transcript text, status text)`.\n"
                "Run the v2.5 SQL migration in Supabase (schema.sql bottom block) and refresh the API schema cache "
                "(Supabase Dashboard → Settings → API → Restart / Reload)."
            ) from e
        if "WEEKLY_LIMIT_REACHED" in msg or "P0001" in msg:
            raise WeeklyQuotaReachedError(msg) from e
        raise
    data = res.data
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return {}


def update_idea(client: Client, idea_id: str, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    res = (
        client.table("ideas")
        .update(fields)
        .eq("id", idea_id)
        .eq("user_id", user_id)
        .execute()
    )
    return res.data[0] if res.data else {}


def admin_reset_ideas_this_week(client: Client, target_user_id: str | None = None) -> int:
    """Admin-only RPC; must use the logged-in admin user's client."""
    params: dict[str, Any] = {}
    if target_user_id:
        params["target_user_id"] = target_user_id
    try:
        res = client.rpc("admin_reset_ideas_this_week", params).execute()
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "PGRST202" in msg and "admin_reset_ideas_this_week" in msg:
            raise MissingRpcError(
                "Missing Supabase RPC `public.admin_reset_ideas_this_week(target_user_id uuid default null)`.\n"
                "Run the v2.5 SQL migration in Supabase and refresh the API schema cache "
                "(Supabase Dashboard → Settings → API → Restart / Reload)."
            ) from e
        if "ADMIN_ONLY" in msg or "42501" in msg:
            raise PermissionError("Solo gli admin possono resettare i crediti settimanali.") from e
        raise
    val = res.data
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int):
        return val
    if isinstance(val, list) and val and isinstance(val[0], int):
        return int(val[0])
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def admin_hall_of_fame() -> list[dict[str, Any]]:
    """Validated ideas sorted by YC final_score, includes author email."""
    client = service_supabase()
    try:
        res = (
            client.table("ideas")
            .select(
                "id, title, vision_score, feasibility_score, dependency_score, "
                "real_feasibility, final_score, yc_verdict, user_id"
            )
            .eq("status", "validated")
            .not_.is_("vision_score", "null")
            .not_.is_("feasibility_score", "null")
            .execute()
        )
        rows = res.data or []
    except Exception as e:  # noqa: BLE001
        # Likely the DB hasn't been migrated yet (missing scoring columns).
        msg = str(e)
        if "does not exist" in msg:
            # Backward-compatible fallback for older DB schema.
            res = (
                client.table("ideas")
                .select("id, title, vision_score, feasibility_score, user_id")
                .eq("status", "validated")
                .not_.is_("vision_score", "null")
                .not_.is_("feasibility_score", "null")
                .execute()
            )
            rows = res.data or []
            for r in rows:
                v = int(r.get("vision_score") or 0)
                f = int(r.get("feasibility_score") or 0)
                d = 50
                rf = round(max(0.0, min(100.0, f - (d * 0.5))), 1)
                final = round(max(0.0, min(100.0, v * (rf / 100.0))), 1)
                r["dependency_score"] = d
                r["real_feasibility"] = rf
                r["final_score"] = final
                r["yc_verdict"] = "BUILD" if rf >= 60 else ("ITERATE" if rf >= 40 else "NOT NOW")
                r["avg_score"] = round((v + f) / 2, 1)
            profiles = {p["id"]: p for p in admin_list_profiles()}
            for r in rows:
                r["author_email"] = profiles.get(r.get("user_id"), {}).get("email")
            rows.sort(
                key=lambda r: (
                    float(r.get("final_score") or 0),
                    int(r.get("vision_score") or 0),
                    float(r.get("real_feasibility") or 0),
                ),
                reverse=True,
            )
            return rows
        raise
    profiles = {p["id"]: p for p in admin_list_profiles()}
    for r in rows:
        r["author_email"] = profiles.get(r.get("user_id"), {}).get("email")
        v = int(r.get("vision_score") or 0)
        f = int(r.get("feasibility_score") or 0)
        d_raw = r.get("dependency_score")
        d = 50 if d_raw is None else int(d_raw)
        rf_raw = r.get("real_feasibility")
        rf = round(max(0.0, min(100.0, f - (d * 0.5))), 1) if rf_raw is None else round(float(rf_raw), 1)
        final_raw = r.get("final_score")
        final = round(max(0.0, min(100.0, v * (rf / 100.0))), 1) if final_raw is None else round(float(final_raw), 1)
        r["dependency_score"] = d
        r["real_feasibility"] = rf
        r["final_score"] = final
        if not r.get("yc_verdict"):
            r["yc_verdict"] = "BUILD" if rf >= 60 else ("ITERATE" if rf >= 40 else "NOT NOW")
        r["avg_score"] = round((v + f) / 2, 1)
    rows.sort(
        key=lambda r: (
            float(r.get("final_score") or 0),
            int(r.get("vision_score") or 0),
            float(r.get("real_feasibility") or 0),
        ),
        reverse=True,
    )
    return rows


def admin_list_profiles() -> list[dict[str, Any]]:
    client = service_supabase()
    res = client.table("profiles").select("*").order("created_at", desc=True).execute()
    return res.data or []


def admin_list_ideas() -> list[dict[str, Any]]:
    client = service_supabase()
    res = client.table("ideas").select("*").order("created_at", desc=True).execute()
    return res.data or []


def admin_set_approved(user_id: str, is_approved: bool) -> dict[str, Any]:
    client = service_supabase()
    res = (
        client.table("profiles")
        .update({"is_approved": is_approved})
        .eq("id", user_id)
        .execute()
    )
    return res.data[0] if res.data else {}


def admin_set_admin(user_id: str, is_admin: bool) -> dict[str, Any]:
    client = service_supabase()
    res = (
        client.table("profiles")
        .update({"is_admin": is_admin})
        .eq("id", user_id)
        .execute()
    )
    return res.data[0] if res.data else {}
