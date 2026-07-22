"""Import a LinkedIn Connections.csv export into the `connections` table.

Usage: python -m agent.import_connections "/path/to/Connections.csv"
Re-runnable: upserts on linkedin_url. Re-export from LinkedIn every few months.
"""
import sys
import csv
import re
from agent import store


def _norm(company: str) -> str:
    c = (company or "").lower().strip()
    c = re.sub(r"[,.]", "", c)
    c = re.sub(r"\b(inc|llc|ltd|corp|co|the|company)\b", "", c)
    return re.sub(r"\s+", " ", c).strip()


def load_rows(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        lines = f.readlines()
    # LinkedIn prepends a few "Notes:" lines before the real header
    start = next(i for i, ln in enumerate(lines) if ln.startswith("First Name,"))
    reader = csv.DictReader(lines[start:])
    rows = []
    for r in reader:
        url = (r.get("URL") or "").strip()
        if not url:
            continue
        rows.append({
            "first_name": (r.get("First Name") or "").strip(),
            "last_name": (r.get("Last Name") or "").strip(),
            "linkedin_url": url,
            "email": (r.get("Email Address") or "").strip() or None,
            "company": (r.get("Company") or "").strip(),
            "company_norm": _norm(r.get("Company") or ""),
            "position": (r.get("Position") or "").strip(),
            "connected_on": (r.get("Connected On") or "").strip(),
        })
    return rows


def main(path: str):
    c = store.get_client()
    rows = load_rows(path)
    for i in range(0, len(rows), 500):
        c.table("connections").upsert(rows[i:i + 500], on_conflict="linkedin_url").execute()
    print(f"imported {len(rows)} connections")


if __name__ == "__main__":
    main(sys.argv[1])
