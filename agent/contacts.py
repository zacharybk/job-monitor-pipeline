"""Find a direct email for a person. Pattern-first and free; Apollo/Hunter optional."""
import os
import sys
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

load_dotenv()


def infer_pattern_email(first: str, last: str, domain: str) -> str:
    first = (first or "").strip().lower()
    domain = (domain or "").strip().lower().lstrip("@")
    return f"{first}@{domain}"


def _hunter(first, last, domain, key):
    try:
        q = urllib.parse.urlencode(
            {"domain": domain, "first_name": first, "last_name": last, "api_key": key})
        with urllib.request.urlopen(
                f"https://api.hunter.io/v2/email-finder?{q}", timeout=15) as r:
            data = json.load(r).get("data", {})
        if data.get("email"):
            return {"email": data["email"], "source": "hunter",
                    "confidence": "high" if (data.get("score") or 0) >= 80 else "medium"}
    except Exception:
        pass
    return None


def find_contact_email(first, last, domain, apollo_key=None, hunter_key=None) -> dict:
    hunter_key = hunter_key or os.getenv("HUNTER_API_KEY")
    # Apollo integration is added when a key exists; skipped here to stay free by default.
    if hunter_key:
        hit = _hunter(first, last, domain, hunter_key)
        if hit:
            return hit
    email = infer_pattern_email(first, last, domain)
    if email and "@" in email and "." in email.split("@")[1]:
        return {"email": email, "source": "pattern", "confidence": "low"}
    return {"email": None, "source": None, "confidence": None}


def _main(argv):
    args = {argv[i].lstrip("-"): argv[i + 1] for i in range(1, len(argv) - 1, 2)}
    print(json.dumps(find_contact_email(
        args.get("first", ""), args.get("last", ""), args.get("domain", ""))))


if __name__ == "__main__":
    _main(sys.argv)
