#!/usr/bin/env python3
"""
One-time migration: local JSON state → Supabase tables.

Run AFTER schema_v2.sql has been applied:
  /Users/zach/.venv/bin/python migrate_state.py
"""
import json
from pathlib import Path
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

SCRIPT_DIR = Path(__file__).parent
client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)


def migrate_seen_jobs():
    path = SCRIPT_DIR / "seen_jobs.json"
    if not path.exists():
        print("seen_jobs.json not found — skipping")
        return
    hashes = json.loads(path.read_text())
    if not isinstance(hashes, list):
        print("seen_jobs.json unexpected format — skipping")
        return
    rows = [{"url_hash": h} for h in hashes if h]
    total = 0
    for i in range(0, len(rows), 500):
        client.table("seen_jobs").upsert(rows[i:i+500], on_conflict="url_hash").execute()
        total += len(rows[i:i+500])
    print(f"Migrated {total} seen job hashes")


def migrate_sources():
    path = SCRIPT_DIR / "job_sources.json"
    if not path.exists():
        print("job_sources.json not found — skipping")
        return
    data = json.loads(path.read_text())
    sources = data.get("sources", [])
    rows = [
        {
            "name":    s["name"],
            "url":     s["url"],
            "type":    s.get("type", "career_page"),
            "enabled": True,
        }
        for s in sources
        if s.get("name") and s.get("url")
    ]
    total = 0
    for i in range(0, len(rows), 500):
        client.table("sources").insert(rows[i:i+500]).execute()
        total += len(rows[i:i+500])
    print(f"Migrated {total} sources")


if __name__ == "__main__":
    migrate_seen_jobs()
    migrate_sources()
