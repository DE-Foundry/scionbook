"""The fixture suite must never contact a live service or use account credentials."""
import pytest
import requests


@pytest.fixture(autouse=True)
def block_live_http(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("Unexpected live HTTP request; supply a synthetic response in this test")
    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", blocked)
    monkeypatch.delenv("LODESTONE_COOKIE", raising=False)
    monkeypatch.delenv("SCIONBOOK_CLIENT", raising=False)
