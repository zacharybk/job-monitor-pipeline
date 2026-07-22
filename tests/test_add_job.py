import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import store


class _Tbl:
    def __init__(self, name, db):
        self.name = name; self.db = db; self._eq = None; self._did_insert = False
    def select(self, *a):
        return self
    def eq(self, col, val):
        self._eq = (col, val); return self
    def insert(self, row):
        self.db.setdefault("inserted", []).append(row); self._did_insert = True; return self
    def execute(self):
        class R: pass
        r = R()
        if self._did_insert:
            r.data = [{"id": "NEWJOB"}]
        elif self._eq and self._eq[0] == "url_hash":
            r.data = self.db.get("existing", [])
        else:
            r.data = []
        return r


class _Client:
    def __init__(self, db): self.db = db
    def table(self, name): return _Tbl(name, self.db)


def test_add_job_inserts_when_new():
    db = {"existing": []}
    jid = store.add_job(_Client(db), {"url": "https://x.co/1", "title": "Head of CX", "company": "Acme"})
    assert jid == "NEWJOB"
    ins = db["inserted"][0]
    assert ins["relevant"] is True and ins["is_active"] is True
    assert ins["url_hash"] == store._job_hash("https://x.co/1")


def test_add_job_returns_existing_id_without_insert():
    db = {"existing": [{"id": "OLD"}]}
    jid = store.add_job(_Client(db), {"url": "https://x.co/1", "title": "X", "company": "Y"})
    assert jid == "OLD"
    assert "inserted" not in db
