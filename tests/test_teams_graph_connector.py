"""Tests for the Microsoft Teams (Graph) connector. Mocked transports only."""

from __future__ import annotations

import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.integrations import teams_graph as TM


def _cfg(**over):
    base = {
        "base_url": "https://graph.example/v1.0",
        "tenant_id": "TEN", "client_id": "CID", "client_secret": "SECRET",
        "team_id": "TEAM", "channel_id": "CHAN", "message_limit": 50,
        "scope": "https://graph.microsoft.com/.default",
        "authority_url": "https://login.microsoftonline.com",
        "timeout_sec": 5, "max_retries": 1,
    }
    base.update(over)
    return base


def _transport(pages_by_marker):
    state = {"auth": None, "urls": []}

    def t(method, url, headers, params, timeout=None):
        if url.endswith("/oauth2/v2.0/token"):
            return {"access_token": "TKN"}
        state["auth"] = headers.get("Authorization")
        state["urls"].append(url)
        for marker, payload in pages_by_marker:
            if marker in url:
                return payload
        return {"value": []}

    return t, state


def test_config_from_env(monkeypatch):
    # team_id/channel_id have empty YAML defaults so env fills them.
    monkeypatch.setenv("ECS_TEAMS_TEAM_ID", "TE")
    monkeypatch.setenv("ECS_TEAMS_CHANNEL_ID", "CH")
    cfg = TM.get_config()
    assert cfg["team_id"] == "TE" and cfg["channel_id"] == "CH"
    assert isinstance(cfg["message_limit"], int)  # resolved (env or default)


def test_masked_config_hides_secrets():
    mc = TM.masked_config(_cfg(client_secret="topsecret"))
    assert mc["client_secret"] == "SET" and "topsecret" not in str(mc)
    assert mc["team_id"] == "SET"


def test_fetch_teams():
    t, _ = _transport([("teams", {"value": [
        {"id": "t1", "displayName": "Audit Team", "visibility": "private"}]})])
    c = TM.TeamsGraphClient(config=_cfg(), transport=t)
    res = c.fetch_teams()
    assert res["ok"] and res["items"][0]["team_id"] == "t1"
    assert res["items"][0]["evidence_type"] == "teams_team"


def test_fetch_channels():
    t, _ = _transport([("/channels", {"value": [
        {"id": "c1", "displayName": "General", "membershipType": "standard"}]})])
    c = TM.TeamsGraphClient(config=_cfg(), transport=t)
    res = c.fetch_channels()
    assert res["ok"] and res["items"][0]["channel_id"] == "c1"


def test_fetch_channels_requires_team():
    c = TM.TeamsGraphClient(config=_cfg(team_id=""))
    assert c.fetch_channels()["ok"] is False


def test_fetch_channel_messages_normalization():
    msg = {"id": "m1", "subject": "Policy update",
           "body": {"content": "<p>Please <b>review</b> the doc</p>"},
           "from": {"user": {"displayName": "Ann"}},
           "createdDateTime": "2026-01-01", "importance": "high", "webUrl": "w"}
    t, state = _transport([("/messages", {"value": [msg]})])
    c = TM.TeamsGraphClient(config=_cfg(), transport=t)
    res = c.fetch_channel_messages()
    m = res["items"][0]
    assert m["message_id"] == "m1" and m["from_user"] == "Ann"
    assert m["body_preview"] == "Please review the doc"  # tags stripped
    assert m["importance"] == "high"
    assert any("/messages" in u for u in state["urls"])


def test_fetch_channel_messages_requires_ids():
    c = TM.TeamsGraphClient(config=_cfg(channel_id=""))
    assert c.fetch_channel_messages(team_id="", channel_id="")["ok"] is False


def test_fetch_channel_tabs():
    t, _ = _transport([("/tabs", {"value": [{"id": "tab1", "displayName": "Wiki"}]})])
    c = TM.TeamsGraphClient(config=_cfg(), transport=t)
    res = c.fetch_channel_tabs()
    assert res["ok"] and res["items"][0]["tab_id"] == "tab1"


def test_auth_header_is_bearer():
    t, state = _transport([("teams", {"value": []})])
    c = TM.TeamsGraphClient(config=_cfg(), transport=t)
    c.fetch_teams()
    assert state["auth"] == "Bearer TKN"


def test_not_configured():
    assert TM.TeamsGraphClient(config={}).fetch_teams()["status"] == "not_configured"


def test_health_check_states(monkeypatch):
    for v in ("ECS_GRAPH_TENANT_ID", "ECS_GRAPH_CLIENT_ID", "ECS_GRAPH_CLIENT_SECRET"):
        monkeypatch.delenv(v, raising=False)
    assert TM.health_check()["status"] == "not_configured"
    assert TM.TeamsGraphClient(config=_cfg()).health_check()["ok"] is True


def test_repr_never_leaks_secret():
    assert "LEAKME" not in repr(TM.TeamsGraphClient(config=_cfg(client_secret="LEAKME")))
