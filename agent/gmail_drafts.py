"""Create Gmail drafts from outreach rows. Never sends — drafts.create only.

Auth is a one-time OAuth flow (see agent/gmail_auth.py). The token lives locally
in agent/.gmail_token.json (gitignored). Our code only ever creates drafts.
"""
import os
import sys
import json
import base64
from email.mime.text import MIMEText

_HERE = os.path.dirname(__file__)
CLIENT_SECRET_PATH = os.path.join(_HERE, ".gmail_client_secret.json")
TOKEN_PATH = os.path.join(_HERE, ".gmail_token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def _build_mime(to: str, subject: str, body: str, sender: str | None = None) -> str:
    """Return the base64url-encoded RFC-2822 message Gmail's API expects."""
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    if sender:
        msg["from"] = sender
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not os.path.exists(TOKEN_PATH):
        raise SystemExit("No Gmail token. Run: /Users/zach/.venv/bin/python -m agent.gmail_auth")
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        else:
            raise SystemExit("Gmail token invalid. Re-run: python -m agent.gmail_auth")
    return build("gmail", "v1", credentials=creds)


def create_draft(service, to: str, subject: str, body: str) -> str:
    raw = _build_mime(to, subject, body)
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}).execute()
    return draft["id"]


def sync(client=None, service=None) -> dict:
    """Create Gmail drafts for every drafted outreach row without one yet."""
    from agent import store
    client = client or store.get_client()
    service = service or get_service()
    rows = (
        client.table("outreach")
        .select("id, contact_id, subject, body, gmail_draft_id")
        .eq("status", "drafted")
        .is_("gmail_draft_id", "null")
        .execute()
    ).data or []
    created, skipped = 0, 0
    for r in rows:
        ct = client.table("contacts").select("email").eq("id", r["contact_id"]).execute().data
        email = ct[0]["email"] if ct else None
        if not email or not r.get("subject") or not r.get("body"):
            skipped += 1
            continue
        did = create_draft(service, email, r["subject"], r["body"])
        client.table("outreach").update({"gmail_draft_id": did}).eq("id", r["id"]).execute()
        created += 1
    return {"drafts_created": created, "skipped": skipped, "candidates": len(rows)}


def _main(argv):
    cmd = argv[1] if len(argv) > 1 else "sync"
    if cmd == "sync":
        print(json.dumps(sync()))
    elif cmd == "test":
        args = {argv[i].lstrip("-"): argv[i + 1] for i in range(2, len(argv) - 1, 2)}
        did = create_draft(get_service(), args["to"],
                           args.get("subject", "Test draft"),
                           args.get("body", "This is a test draft. Delete me."))
        print(did)


if __name__ == "__main__":
    _main(sys.argv)
