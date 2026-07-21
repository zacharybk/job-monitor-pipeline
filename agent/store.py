"""Deterministic Supabase I/O for the morning agent. CLI + importable funcs."""
import os
import sys
import json as _json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def save_pick(client: Client, p: dict) -> str:
    row = {k: p.get(k) for k in
           ("job_id", "fit_verdict", "fit_rubric", "reasoning", "angle", "rank", "tier")}
    res = client.table("picks").upsert(row, on_conflict="job_id").execute()
    client.table("jobs").update({"reviewed_at": _now()}).eq("id", p["job_id"]).execute()
    return (res.data or [{}])[0].get("id", "ok")


def mark_skipped(client: Client, job_id: str, reasoning: str) -> str:
    client.table("jobs").update(
        {"reviewed_at": _now(), "user_feedback": f"SKIP: {reasoning}"}
    ).eq("id", job_id).execute()
    return "ok"


def save_contact(client: Client, p: dict) -> str:
    row = {k: p.get(k) for k in
           ("company", "name", "role", "email", "email_source",
            "confidence", "linkedin_url", "job_id")}
    res = client.table("contacts").upsert(row, on_conflict="company,name").execute()
    return (res.data or [{}])[0].get("id", "ok")


def save_outreach(client: Client, p: dict) -> str:
    row = {k: p.get(k) for k in
           ("contact_id", "job_id", "track", "sequence_step", "subject", "body")}
    row.setdefault("sequence_step", 1)
    row.setdefault("track", "job")
    res = client.table("outreach").upsert(
        row, on_conflict="contact_id,track,sequence_step").execute()
    return (res.data or [{}])[0].get("id", "ok")


def save_application(client: Client, p: dict) -> str:
    row = {k: p.get(k) for k in ("job_id", "cover_letter_path", "notes")}
    res = client.table("applications").upsert(row, on_conflict="job_id").execute()
    return (res.data or [{}])[0].get("id", "ok")


def log_activity(client: Client, p: dict) -> str:
    row = {"day": datetime.now(timezone.utc).date().isoformat(), "agent_ran_at": _now()}
    for k in ("jobs_reviewed", "picks_made", "emails_drafted", "emails_sent",
              "applications_sent", "replies"):
        if k in p:
            row[k] = p[k]
    if "discovery_notes" in p:
        row["discovery_notes"] = p["discovery_notes"]
    if "summary" in p:
        row["summary"] = p["summary"]
    client.table("activity_log").upsert(row, on_conflict="day").execute()
    return "ok"


_COMMANDS = {
    "get-jobs-to-review": lambda c, a: get_jobs_to_review(c, int(a.get("limit", 100))),
    "get-due-followups":  lambda c, a: get_due_followups(c),
    "save-pick":          lambda c, a: save_pick(c, a),
    "mark-skipped":       lambda c, a: mark_skipped(c, a["job_id"], a.get("reasoning", "")),
    "save-contact":       lambda c, a: save_contact(c, a),
    "save-outreach":      lambda c, a: save_outreach(c, a),
    "save-application":   lambda c, a: save_application(c, a),
    "log-activity":       lambda c, a: log_activity(c, a),
}


def _main(argv):
    cmd = argv[1]
    payload = {}
    if "--json" in argv:
        payload = _json.loads(argv[argv.index("--json") + 1])
    if "--limit" in argv:
        payload["limit"] = argv[argv.index("--limit") + 1]
    result = _COMMANDS[cmd](get_client(), payload)
    print(_json.dumps(result) if not isinstance(result, str) else result)


if __name__ == "__main__":
    _main(sys.argv)
