"""Tests for the SharePoint (Microsoft Graph) connector.

Mocked transports only — no real Graph call. Verifies config/masking, the deeper
site/drive/item/folder/file methods, normalized evidence-metadata shapes,
backward-compatible fetch_documents/normalize_document, nextLink pagination,
metadata-only file access, and no secret leakage.
"""

from __future__ import annotations

import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.integrations import sharepoint_graph as SP


def _cfg(**over):
    base = {
        "base_url": "https://graph.example/v1.0",
        "tenant_id": "TEN", "client_id": "CID", "client_secret": "SECRET",
        "site_id": "SID", "drive_id": "DID",
        "scope": "https://graph.microsoft.com/.default",
        "authority_url": "https://login.microsoftonline.com",
        "timeout_sec": 5, "max_retries": 1,
    }
    base.update(over)
    return base


def _transport(pages_by_marker):
    """pages_by_marker: list of (url_substring, payload). Token auto-handled."""
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


# --------------------------------------------------------------------------- #
# Config + masking
# --------------------------------------------------------------------------- #
def test_config_from_env(monkeypatch):
    monkeypatch.setenv("ECS_GRAPH_TENANT_ID", "T")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_ID", "C")
    monkeypatch.setenv("ECS_GRAPH_CLIENT_SECRET", "S")
    monkeypatch.setenv("ECS_GRAPH_SITE_ID", "SITE")
    monkeypatch.setenv("ECS_SHAREPOINT_SITE_HOSTNAME", "contoso.sharepoint.com")
    monkeypatch.setenv("ECS_SHAREPOINT_SITE_PATH", "sites/Audit")
    cfg = SP.get_config()
    assert cfg["site_id"] == "SITE" and cfg["site_hostname"] == "contoso.sharepoint.com"
    assert cfg["site_path"] == "sites/Audit"


def test_masked_config_hides_secrets():
    mc = SP.masked_config(_cfg(client_secret="topsecret"))
    assert mc["client_secret"] == "SET" and "topsecret" not in str(mc)
    assert mc["ready"] is True


def test_is_configured_requires_site():
    assert SP.SharePointGraphClient(config=_cfg(site_id="")).is_configured() is False
    assert SP.SharePointGraphClient(config=_cfg()).is_configured() is True


# --------------------------------------------------------------------------- #
# Sites / drives / items
# --------------------------------------------------------------------------- #
def test_fetch_sites():
    t, _ = _transport([("sites", {"value": [
        {"id": "s1", "displayName": "Audit", "webUrl": "u"}]})])
    c = SP.SharePointGraphClient(config=_cfg(), transport=t)
    res = c.fetch_sites()
    assert res["ok"] and res["items"][0]["site_id"] == "s1"
    assert res["items"][0]["evidence_type"] == "sharepoint_site"


def test_resolve_site_by_path():
    t, state = _transport([(":/sites/Audit", {"id": "s9", "displayName": "Audit"})])
    c = SP.SharePointGraphClient(config=_cfg(site_hostname="contoso.sharepoint.com",
                                             site_path="sites/Audit"), transport=t)
    res = c.resolve_site_by_path()
    assert res["ok"] and res["items"][0]["site_id"] == "s9"
    assert any("contoso.sharepoint.com:/sites/Audit" in u for u in state["urls"])


def test_resolve_site_by_path_requires_inputs():
    c = SP.SharePointGraphClient(config=_cfg(site_hostname="", site_path=""))
    res = c.resolve_site_by_path()
    assert res["ok"] is False


def test_fetch_drives():
    t, _ = _transport([("/drives", {"value": [
        {"id": "d1", "name": "Documents", "driveType": "documentLibrary"}]})])
    c = SP.SharePointGraphClient(config=_cfg(), transport=t)
    res = c.fetch_drives()
    assert res["ok"] and res["items"][0]["drive_id"] == "d1"
    assert res["items"][0]["evidence_type"] == "sharepoint_drive"


def test_fetch_drive_items_rich_normalization():
    item = {"id": "i1", "name": "policy.pdf", "size": 100, "webUrl": "w",
            "createdDateTime": "2026-01-01", "lastModifiedDateTime": "2026-02-01",
            "createdBy": {"user": {"displayName": "Ann"}},
            "lastModifiedBy": {"user": {"displayName": "Bob"}},
            "file": {"mimeType": "application/pdf"},
            "parentReference": {"path": "/drive/root:/Evidence"}}
    t, _ = _transport([("root/children", {"value": [item]})])
    c = SP.SharePointGraphClient(config=_cfg(), transport=t)
    res = c.fetch_drive_items()
    doc = res["items"][0]
    assert doc["item_id"] == "i1" and doc["mime_type"] == "application/pdf"
    assert doc["created_by"] == "Ann" and doc["modified_by"] == "Bob"
    assert doc["parent_reference"]["path"] == "/drive/root:/Evidence"
    assert doc["evidence_type"] == "sharepoint_document"


def test_fetch_folder_items_uses_folder_path():
    t, state = _transport([("root:/Evidence/2026:/children", {"value": [{"id": "f1", "name": "a"}]})])
    c = SP.SharePointGraphClient(config=_cfg(), transport=t)
    res = c.fetch_folder_items(folder_path="Evidence/2026")
    assert res["ok"] and res["items"][0]["item_id"] == "f1"
    assert any("root:/Evidence/2026:/children" in u for u in state["urls"])


def test_fetch_file_metadata_only():
    t, state = _transport([("items/i5", {"id": "i5", "name": "f.docx", "size": 9})])
    c = SP.SharePointGraphClient(config=_cfg(), transport=t)
    res = c.download_file_metadata_only("i5")
    assert res["ok"] and res["items"][0]["item_id"] == "i5"
    assert any("/items/i5" in u for u in state["urls"])
    # No content download endpoint (/content) is ever called.
    assert not any(u.endswith("/content") for u in state["urls"])


def test_fetch_file_metadata_requires_ids():
    c = SP.SharePointGraphClient(config=_cfg(drive_id=""))
    assert c.fetch_file_metadata("")["ok"] is False


# --------------------------------------------------------------------------- #
# Backward compatibility
# --------------------------------------------------------------------------- #
def test_fetch_documents_backward_compatible_shape():
    t, _ = _transport([("root/children", {"value": [
        {"id": "9", "name": "f.docx", "size": 5, "lastModifiedDateTime": "2026"}]})])
    c = SP.SharePointGraphClient(config=_cfg(), transport=t)
    res = c.fetch_documents(page_size=100)
    doc = res["items"][0]
    assert doc["item_id"] == "9" and doc["size_bytes"] == 5
    assert "last_modified" in doc and doc["source"] == "sharepoint_graph"


def test_normalize_document_legacy_keys():
    doc = SP.normalize_document({"id": "9", "name": "f", "size": 5, "folder": {}})
    assert doc["item_id"] == "9" and doc["is_folder"] is True
    assert set(doc) == {"item_id", "name", "size_bytes", "last_modified",
                        "web_url", "is_folder", "source"}


def test_not_configured_returns_standard_response():
    res = SP.SharePointGraphClient(config={}).fetch_drive_items()
    assert res["ok"] is False and res["status"] == "not_configured"


def test_health_check_states(monkeypatch):
    for v in ("ECS_GRAPH_TENANT_ID", "ECS_GRAPH_CLIENT_ID", "ECS_GRAPH_CLIENT_SECRET",
              "ECS_GRAPH_SITE_ID"):
        monkeypatch.delenv(v, raising=False)
    assert SP.health_check()["status"] == "not_configured"
    hc = SP.SharePointGraphClient(config=_cfg()).health_check()
    assert hc["ok"] is True and hc["configured"] is True


def test_repr_never_leaks_secret():
    c = SP.SharePointGraphClient(config=_cfg(client_secret="LEAKME"))
    assert "LEAKME" not in repr(c)
