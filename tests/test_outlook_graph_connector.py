"""Tests for the Outlook Email (Graph) connector. Mocked transports only.

Verifies config/masking, mail folder / message / attachment-metadata fetches,
normalized shapes, that attachment CONTENTS are never requested, and no secret
leakage.
"""

from __future__ import annotations

import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.integrations import outlook_graph as OL


def _cfg(**over):
    base = {
        "base_url": "https://graph.example/v1.0",
        "tenant_id": "TEN", "client_id": "CID", "client_secret": "SECRET",
        "user_id": "user@x.com", "mail_folder": "inbox", "message_limit": 50,
        "scope": "https://graph.microsoft.com/.default",
        "authority_url": "https://login.microsoftonline.com",
        "timeout_sec": 5, "max_retries": 1,
    }
    base.update(over)
    return base


def _transport(pages_by_marker):
    state = {"auth": None, "urls": [], "params": []}

    def t(method, url, headers, params, timeout=None):
        if url.endswith("/oauth2/v2.0/token"):
            return {"access_token": "TKN"}
        state["auth"] = headers.get("Authorization")
        state["urls"].append(url)
        state["params"].append(params)
        for marker, payload in pages_by_marker:
            if marker in url:
                return payload
        return {"value": []}

    return t, state


def test_config_from_env(monkeypatch):
    # user_id has an empty YAML default so env fills it.
    monkeypatch.setenv("ECS_OUTLOOK_USER_ID", "svc@x.com")
    cfg = OL.get_config()
    assert cfg["user_id"] == "svc@x.com"
    assert cfg["mail_folder"]  # resolved (env or default 'inbox')


def test_is_configured_requires_user():
    assert OL.OutlookGraphClient(config=_cfg(user_id="")).is_configured() is False
    assert OL.OutlookGraphClient(config=_cfg()).is_configured() is True


def test_masked_config_hides_secrets():
    mc = OL.masked_config(_cfg(client_secret="topsecret"))
    assert mc["client_secret"] == "SET" and "topsecret" not in str(mc)
    assert mc["user_id"] == "SET"


def test_fetch_mail_folders():
    t, _ = _transport([("mailFolders", {"value": [
        {"id": "f1", "displayName": "Inbox", "totalItemCount": 10, "unreadItemCount": 2}]})])
    c = OL.OutlookGraphClient(config=_cfg(), transport=t)
    res = c.fetch_mail_folders()
    assert res["ok"] and res["items"][0]["folder_id"] == "f1"
    assert res["items"][0]["total_item_count"] == 10


def test_fetch_messages_normalization():
    msg = {"id": "e1", "subject": "Audit request",
           "sender": {"emailAddress": {"address": "a@x.com"}},
           "toRecipients": [{"emailAddress": {"address": "b@x.com"}},
                            {"emailAddress": {"address": "c@x.com"}}],
           "receivedDateTime": "2026-01-01", "hasAttachments": True,
           "importance": "normal", "bodyPreview": "hello", "webLink": "w"}
    t, _ = _transport([("/messages", {"value": [msg]})])
    c = OL.OutlookGraphClient(config=_cfg(), transport=t)
    res = c.fetch_messages()
    m = res["items"][0]
    assert m["message_id"] == "e1" and m["sender"] == "a@x.com"
    assert m["recipients"] == ["b@x.com", "c@x.com"]
    assert m["has_attachments"] is True and m["evidence_type"] == "outlook_message"


def test_fetch_messages_requires_user():
    c = OL.OutlookGraphClient(config=_cfg(user_id=""))
    assert c.fetch_messages()["ok"] is False


def test_fetch_message_single():
    t, state = _transport([("/messages/e9", {"id": "e9", "subject": "S",
                                             "sender": {"emailAddress": {"address": "z@x.com"}}})])
    c = OL.OutlookGraphClient(config=_cfg(), transport=t)
    res = c.fetch_message(message_id="e9")
    assert res["ok"] and res["items"][0]["message_id"] == "e9"


def test_fetch_attachments_metadata_only():
    att = {"id": "a1", "name": "report.pdf", "contentType": "application/pdf",
           "size": 2048, "isInline": False, "lastModifiedDateTime": "2026-01-01"}
    t, state = _transport([("/attachments", {"value": [att]})])
    c = OL.OutlookGraphClient(config=_cfg(), transport=t)
    res = c.fetch_attachments_metadata(message_id="e1")
    a = res["items"][0]
    assert a["attachment_id"] == "a1" and a["content_type"] == "application/pdf"
    assert a["size"] == 2048 and a["evidence_type"] == "outlook_attachment"
    # $select must exclude contentBytes (no attachment content is fetched).
    select = state["params"][-1].get("$select", "")
    assert "contentBytes" not in select and "name" in select


def test_auth_header_is_bearer():
    t, state = _transport([("mailFolders", {"value": []})])
    c = OL.OutlookGraphClient(config=_cfg(), transport=t)
    c.fetch_mail_folders()
    assert state["auth"] == "Bearer TKN"


def test_not_configured():
    assert OL.OutlookGraphClient(config={}).fetch_messages()["status"] == "not_configured"


def test_health_check_states(monkeypatch):
    for v in ("ECS_GRAPH_TENANT_ID", "ECS_GRAPH_CLIENT_ID", "ECS_GRAPH_CLIENT_SECRET",
              "ECS_OUTLOOK_USER_ID"):
        monkeypatch.delenv(v, raising=False)
    assert OL.health_check()["status"] == "not_configured"
    assert OL.OutlookGraphClient(config=_cfg()).health_check()["ok"] is True


def test_repr_never_leaks_secret():
    assert "LEAKME" not in repr(OL.OutlookGraphClient(config=_cfg(client_secret="LEAKME")))
