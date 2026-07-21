import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import contacts


def test_infer_pattern_email():
    assert contacts.infer_pattern_email("Jane", "Doe", "Acme.com") == "jane@acme.com"
    assert contacts.infer_pattern_email(" Jane ", "", "acme.com") == "jane@acme.com"


def test_find_falls_back_to_pattern_when_no_keys(monkeypatch):
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    r = contacts.find_contact_email("Jane", "Doe", "acme.com")
    assert r == {"email": "jane@acme.com", "source": "pattern", "confidence": "low"}
