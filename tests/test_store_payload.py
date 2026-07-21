import sys, os, json, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import store


def test_load_payload_from_file_preserves_apostrophes(tmp_path):
    p = tmp_path / "o.json"
    p.write_text(json.dumps({"body": "I've built that. You're right; it'd help."}))
    got = store._load_payload(["save-outreach", "--json-file", str(p)])
    assert got["body"] == "I've built that. You're right; it'd help."


def test_load_payload_from_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"body": "don\'t drop this"}'))
    got = store._load_payload(["save-outreach", "--json", "-"])
    assert got["body"] == "don't drop this"


def test_load_payload_inline_still_works():
    got = store._load_payload(["save-pick", "--json", '{"job_id": "J1"}'])
    assert got == {"job_id": "J1"}
