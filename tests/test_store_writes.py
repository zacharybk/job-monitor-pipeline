import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import store


class FakeTable:
    def __init__(self, sink):
        self.sink = sink

    def upsert(self, payload, **kw):
        self.sink.append(("upsert", payload, kw))
        return self

    def update(self, payload):
        self.sink.append(("update", payload))
        return self

    def eq(self, *a):
        self.sink.append(("eq", a))
        return self

    def execute(self):
        class R:
            data = [{"id": "NEWID"}]
        return R()


class FakeClient:
    def __init__(self):
        self.calls = []

    def table(self, name):
        self.calls.append(name)
        return FakeTable(self.calls)


def test_save_pick_upserts_and_marks_job_reviewed():
    c = FakeClient()
    pid = store.save_pick(c, {"job_id": "J1", "fit_verdict": "apply",
                              "reasoning": "r", "rank": 1, "tier": "top"})
    assert pid == "NEWID"
    assert "picks" in c.calls and "jobs" in c.calls


def test_save_outreach_uses_conflict_key():
    c = FakeClient()
    store.save_outreach(c, {"contact_id": "C1", "track": "job",
                            "sequence_step": 1, "subject": "s", "body": "b"})
    upserts = [x for x in c.calls if isinstance(x, tuple) and x[0] == "upsert"]
    assert any("contact_id" in u[2].get("on_conflict", "") for u in upserts)
