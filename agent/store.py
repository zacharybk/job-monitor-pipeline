"""Deterministic Supabase I/O for the morning agent. CLI + importable funcs."""
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def get_client() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def get_jobs_to_review(client: Client, limit: int = 100) -> list[dict]:
    picked = client.table("picks").select("job_id").execute().data or []
    picked_ids = {r["job_id"] for r in picked}
    rows = (
        client.table("jobs")
        .select("id, title, company, location, description, url")
        .eq("relevant", True)
        .eq("is_active", True)
        .is_("reviewed_at", "null")
        .order("created_at", desc=True)
        .limit(limit + len(picked_ids))
        .execute()
    ).data or []
    out = [r for r in rows if r["id"] not in picked_ids]
    return out[:limit]


def get_due_followups(client: Client) -> list[dict]:
    now = datetime.now(timezone.utc)
    rows = (
        client.table("outreach")
        .select("id, contact_id, job_id, track, sequence_step, sent_at")
        .eq("status", "sent")
        .lt("sequence_step", 3)
        .execute()
    ).data or []
    due = []
    for r in rows:
        if not r.get("sent_at"):
            continue
        sent = datetime.fromisoformat(r["sent_at"].replace("Z", "+00:00"))
        threshold = timedelta(days=4 if r["sequence_step"] == 1 else 5)
        if now - sent >= threshold:
            due.append(r)
    return due
