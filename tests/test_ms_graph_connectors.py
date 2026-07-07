"""Tests for the shared Microsoft Graph connector foundation (ms_graph_base).

All transports are mocked — NO real Graph call is made. Verifies config loading
(env + YAML placeholders), secret masking, OAuth2 client-credentials token
exchange + caching, Bearer auth-header assembly, ``@odata.nextLink`` pagination,
error normalization, secret-safe repr, and health_check configured/missing states.
"""

from __future__ import annotations

import base64
import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.integrations import _base
from modules.operations.integrations import ms_graph_base as G


@pytest.fixture(autouse=True)
def _fresh_config_cache():
    """Isolate env-config resolution per test (clears the loader's lru_cache)."""
    try:
        from config.environment_loader import get_environment_config
        get_environment_config(refresh=True)
    except Exception:  # noqa: BLE001
        pass
    yield
    try:
        from config.environment_loader import get_environment_config
        get_environment_config(refresh=True)
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _cfg(**over):
    base = {
        "base_url": "https://graph.example/v1.0",
        "tenant_id": "TEN", "client_id": "CID", "client_secret": "SECRET",
        "scope": G.GRAPH_SCOPE, "authority_url": G.DEFAULT_AUTHORITY,
        "timeout_sec": 5, "max_retries": 1,
    }
    base.update(over)
    return base


class _Adapter(G.GraphAdapter):
    source: str = "ms_graph_test"


def _token_transport(token="MINTED", pages=None):
    pages = pages or [{"value": []}]
    state = {"auth": None, "data_calls": 0, "token_calls": 0}

    def t(method, url, headers, params, timeout=None):
        if url.endswith("/oauth2/v2.0/token"):
            state["token_calls"] += 1
            assert params["grant_type"] == "client_credentials"
            assert params["client_id"] == "CID"
            return {"access_token": token, "expires_in": 3600} if token else {}
        state["auth"] = headers.get("Authorization")
        idx = min(state["data_calls"], len(pages) - 1)
        state["data_calls"] += 1
        return pages[idx]

    return t, state


# --------------------------------------------------------------------------- #
# Config + masking
# --------------------------------------------------------------------------- #
def test_get_graph_config_from_env(monkeypatch):
    monkeypatch.setenv("ECS_GRAPH_TENANT_ID", "T1")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_ID", "C1")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_SECRET", "supersecret")
    monkeypatch.setenv("ECS_GRAPH_SCOPE", "custom/.default")
    # Refresh AFTER setting env so the YAML ${VAR} defaults re-resolve with it.
    from config.environment_loader import get_environment_config
    get_environment_config(refresh=True)
    cfg = G.get_graph_config()
    assert cfg["tenant_id"] == "T1" and cfg["client_id"] == "C1"
    assert cfg["scope"] == "custom/.default"
    assert cfg["client_secret"] == "supersecret"


def test_get_graph_config_defaults():
    cfg = G.get_graph_config()
    assert cfg["base_url"] == G.GRAPH_BASE
    assert cfg["scope"] == G.GRAPH_SCOPE
    assert cfg["authority_url"] == G.DEFAULT_AUTHORITY


def test_is_graph_configured():
    assert G.is_graph_configured(_cfg()) is True
    assert G.is_graph_configured({"tenant_id": "", "client_id": "C", "client_secret": "S"}) is False


def test_graph_masked_config_hides_secrets():
    mc = G.graph_masked_config(_cfg(client_secret="topsecret"))
    assert mc["client_secret"] == "SET" and mc["tenant_id"] == "SET"
    assert "topsecret" not in str(mc)


def test_normalize_error_shape():
    e = G.normalize_error("auth_error", "bad token")
    assert e["ok"] is False and e["status"] == "auth_error" and "bad token" in e["detail"]


# --------------------------------------------------------------------------- #
# Token exchange + caching
# --------------------------------------------------------------------------- #
def test_authenticate_exchanges_token():
    t, state = _token_transport()
    a = _Adapter(config=_cfg(), transport=t)
    assert a.authenticate() == "MINTED"
    assert state["token_calls"] == 1


def test_authenticate_is_cached():
    t, state = _token_transport()
    a = _Adapter(config=_cfg(), transport=t)
    assert a.authenticate() == "MINTED"
    assert a.authenticate() == "MINTED"
    assert state["token_calls"] == 1  # cached, only one exchange


def test_authenticate_failure_cached_not_reattempted():
    t, state = _token_transport(token=None)  # token endpoint returns no token
    a = _Adapter(config=_cfg(), transport=t)
    assert a.authenticate() is None
    assert a.authenticate() is None
    assert state["token_calls"] == 1


def test_configured_access_token_used_without_exchange():
    t, state = _token_transport()
    a = _Adapter(config=_cfg(access_token="PRESET"), transport=t)
    assert a.authenticate() == "PRESET"
    assert state["token_calls"] == 0  # no exchange when token preset


def test_authenticate_without_transport_returns_none():
    a = _Adapter(config=_cfg())  # no transport (skeleton)
    assert a.authenticate() is None


def test_auth_headers_bearer_after_auth():
    t, _ = _token_transport()
    a = _Adapter(config=_cfg(), transport=t)
    a.authenticate()
    assert a.auth_headers() == {"Authorization": "Bearer MINTED"}


def test_auth_headers_empty_before_auth():
    a = _Adapter(config=_cfg())
    assert a.auth_headers() == {}  # no implicit exchange


def test_token_url_uses_authority_and_tenant():
    a = _Adapter(config=_cfg(tenant_id="TENANT9"))
    assert a._token_url() == "https://login.microsoftonline.com/TENANT9/oauth2/v2.0/token"


def test_token_url_override():
    a = _Adapter(config=_cfg(token_url="https://custom/token"))
    assert a._token_url() == "https://custom/token"


# --------------------------------------------------------------------------- #
# Pagination (nextLink)
# --------------------------------------------------------------------------- #
def test_graph_collect_follows_nextlink():
    p1 = {"value": [{"id": "1"}], "@odata.nextLink": "https://graph.example/next"}
    p2 = {"value": [{"id": "2"}]}
    t, state = _token_transport(pages=[p1, p2])
    a = _Adapter(config=_cfg(), transport=t)
    res = a.graph_collect("things", lambda r: {"id": r.get("id")}, max_items=100)
    assert res["ok"] and [x["id"] for x in res["items"]] == ["1", "2"]
    assert state["data_calls"] == 2  # both pages fetched


def test_graph_collect_respects_max_items():
    p1 = {"value": [{"id": str(i)} for i in range(5)], "@odata.nextLink": "u"}
    t, _ = _token_transport(pages=[p1])
    a = _Adapter(config=_cfg(), transport=t)
    res = a.graph_collect("things", lambda r: r, max_items=3)
    assert len(res["items"]) == 3


def test_graph_collect_stops_without_nextlink():
    t, state = _token_transport(pages=[{"value": [{"id": "1"}]}])
    a = _Adapter(config=_cfg(), transport=t)
    res = a.graph_collect("things", lambda r: r)
    assert len(res["items"]) == 1 and state["data_calls"] == 1


def test_graph_collect_not_configured():
    a = _Adapter(config={"tenant_id": ""})
    res = a.graph_collect("things", lambda r: r)
    assert res["ok"] is False and res["status"] == "not_configured"


def test_graph_collect_classifies_transport_error():
    def t(method, url, headers, params, timeout=None):
        if url.endswith("/token"):
            return {"access_token": "X"}
        raise TimeoutError("timed out")
    a = _Adapter(config=_cfg(max_retries=0), transport=t)
    res = a.graph_collect("things", lambda r: r)
    assert res["ok"] is False and res["status"] == "timeout"


def test_graph_get_one():
    def t(method, url, headers, params, timeout=None):
        if url.endswith("/token"):
            return {"access_token": "X"}
        return {"id": "single", "displayName": "One"}
    a = _Adapter(config=_cfg(), transport=t)
    res = a.graph_get_one("things/single", lambda r: {"id": r["id"]})
    assert res["ok"] and res["items"][0]["id"] == "single"


# --------------------------------------------------------------------------- #
# health_check + repr
# --------------------------------------------------------------------------- #
def test_module_health_check_not_configured(monkeypatch):
    for v in ("ECS_GRAPH_TENANT_ID", "ECS_GRAPH_CLIENT_ID", "ECS_GRAPH_CLIENT_SECRET"):
        monkeypatch.delenv(v, raising=False)
    hc = G.health_check()
    assert hc["status"] == "not_configured" and hc["configured"] is False


def test_module_health_check_configured(monkeypatch):
    monkeypatch.setenv("ECS_GRAPH_TENANT_ID", "T")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_ID", "C")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_SECRET", "S")
    hc = G.health_check()
    assert hc["ok"] is True and hc["configured"] is True


def test_repr_never_leaks_secret():
    a = _Adapter(config=_cfg(client_secret="LEAKME123"))
    assert "LEAKME123" not in repr(a)
    assert "SET" in repr(a)


def test_identity_name_helper():
    assert G.identity_name({"user": {"displayName": "Ann"}}) == "Ann"
    assert G.identity_name({"displayName": "Bob"}) == "Bob"
    assert G.identity_name(None) == ""
