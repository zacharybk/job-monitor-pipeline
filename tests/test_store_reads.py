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
