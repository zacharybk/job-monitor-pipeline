import sys, os, base64
from email import message_from_bytes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import gmail_drafts


def test_build_mime_preserves_apostrophes_and_headers():
    raw = gmail_drafts._build_mime("dan@mabl.com", "Hello", "I've built that. You're set.")
    decoded = base64.urlsafe_b64decode(raw)
    msg = message_from_bytes(decoded)
    assert msg["To"] == "dan@mabl.com"
    assert msg["Subject"] == "Hello"
    assert "I've built that. You're set." in msg.get_payload(decode=True).decode()


class _FakeExec:
    def __init__(self, ret): self._ret = ret
    def execute(self): return self._ret

class _FakeDrafts:
    def __init__(self, sink): self.sink = sink
    def create(self, userId, body):
        self.sink.append(body)
        return _FakeExec({"id": "DRAFT123"})

class _FakeUsers:
    def __init__(self, sink): self.sink = sink
    def drafts(self): return _FakeDrafts(self.sink)

class _FakeService:
    def __init__(self): self.sink = []
    def users(self): return _FakeUsers(self.sink)


class _Tbl:
    def __init__(self, name, db): self.name=name; self.db=db; self._sel=None; self._eqs=[]
    def select(self, *a, **k): self._sel=a; return self
    def eq(self, col, val): self._eqs.append((col,val)); return self
    def is_(self, col, val): self._eqs.append((col,val)); return self
    def update(self, payload): self.db["updates"].append((self.name,payload,self._eqs)); return self
    def execute(self):
        class R: pass
        r=R()
        if self.name=="outreach" and not any(u for u in self.db["updates"] if u): pass
        r.data = self.db.get(self.name, [])
        return r

class _FakeClient:
    def __init__(self, db): self.db=db
    def table(self, name): return _Tbl(name, self.db)


def test_sync_creates_draft_and_records_id():
    db = {
        "outreach": [{"id":"O1","contact_id":"C1","subject":"S","body":"B","gmail_draft_id":None}],
        "contacts": [{"email":"dan@mabl.com"}],
        "updates": [],
    }
    svc = _FakeService()
    out = gmail_drafts.sync(client=_FakeClient(db), service=svc)
    assert out["drafts_created"] == 1
    assert svc.sink and "raw" in svc.sink[0]["message"]
    assert any(u[0]=="outreach" and u[1]=={"gmail_draft_id":"DRAFT123"} for u in db["updates"])


def test_sync_skips_when_no_email():
    db = {
        "outreach": [{"id":"O1","contact_id":"C1","subject":"S","body":"B","gmail_draft_id":None}],
        "contacts": [],
        "updates": [],
    }
    out = gmail_drafts.sync(client=_FakeClient(db), service=_FakeService())
    assert out["drafts_created"] == 0 and out["skipped"] == 1
