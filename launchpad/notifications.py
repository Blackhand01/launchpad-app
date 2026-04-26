"""Email notifications for admin and score alerts."""

from __future__ import annotations

import os

import resend


def notify_admin_new_signup(email: str) -> None:
    key = os.getenv("RESEND_API_KEY")
    to_addr = os.getenv("ADMIN_NOTIFICATION_EMAIL")
    from_addr = os.getenv("RESEND_FROM_EMAIL")
    if not key or not to_addr or not from_addr:
        return
    resend.api_key = key
    resend.Emails.send(
        {
            "from": from_addr,
            "to": [to_addr],
            "subject": "Launchpad: nuova richiesta di accesso",
            "html": f"<p>Nuovo utente registrato: <strong>{email}</strong></p>"
            "<p>Approvazione richiesta in Supabase (<code>profiles.is_approved</code>).</p>",
        }
    )


def notify_high_vision_alert(
    *,
    idea_title: str,
    author_email: str,
    vision_score: int,
    feasibility_score: int,
) -> None:
    if vision_score <= 80:
        return
    key = os.getenv("RESEND_API_KEY")
    to_addr = os.getenv("HIGH_VISION_ALERT_EMAIL") or os.getenv("ADMIN_NOTIFICATION_EMAIL")
    from_addr = os.getenv("RESEND_FROM_EMAIL")
    if not key or not to_addr or not from_addr:
        return
    resend.api_key = key
    resend.Emails.send(
        {
            "from": from_addr,
            "to": [to_addr],
            "subject": f"Launchpad: vision alta ({vision_score}) — {idea_title[:80]}",
            "html": (
                f"<p><strong>Vision score:</strong> {vision_score} · "
                f"<strong>Feasibility:</strong> {feasibility_score}</p>"
                f"<p><strong>Idea:</strong> {idea_title}</p>"
                f"<p><strong>Autore:</strong> {author_email}</p>"
            ),
        }
    )
