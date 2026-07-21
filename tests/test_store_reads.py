import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import store


def test_get_client_reads_env(monkeypatch):
    captured = {}
    monkeypatch.setattr(store, "create_client",
                        lambda url, key: captured.update(url=url, key=key) or "CLIENT")
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")
    assert store.get_client() == "CLIENT"
    assert captured == {"url": "https://x.supabase.co", "key": "svc"}


class _Chain:
    def __init__(self, sink):
        self.sink = sink
    def select(self, *a, **k):
        return self
    def eq(self, *a):
        return self
    def is_(self, *a):
        return self
    def gte(self, col, val):
        self.sink["gte"] = (col, val)
        return self
    def order(self, col, **k):
        self.sink["order"] = (col, k.get("desc"))
        return self
    def limit(self, n):
        return self
    def execute(self):
        class R:
            data = []
        return R()


class _Client:
    def __init__(self):
        self.sink = {}
    def table(self, name):
        return _Chain(self.sink)


def test_get_jobs_to_review_filters_and_sorts_by_last_seen():
    c = _Client()
    store.get_jobs_to_review(c, limit=10, max_age_days=14)
    assert c.sink["gte"][0] == "last_seen"      # freshness cutoff applied
    assert c.sink["order"] == ("last_seen", True)  # freshest first
