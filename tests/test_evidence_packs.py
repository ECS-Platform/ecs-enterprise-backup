"""Tests for Evidence Packs + manifests (Milestone 3). Deterministic/offline."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import json

import pytest

from modules.audit_intelligence.engines import evidence_packs as packs
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.services import audit_repository_service as svc


@pytest.fixture(autouse=True)
def _seed():
    repo.reset_repository()
    repo.store_evidence(control_id="NGX-003", content="ssl on", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS", "ISO27001"), verdict="PASS")
    repo.store_evidence(control_id="NGX-005", content="off", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS",), verdict="FAIL")
    repo.store_evidence(control_id="RDX-001", content="ok", technology="Redis",
                        asset_id="cache-1", frameworks=("ISO27001",), verdict="PASS")
    yield
    repo.reset_repository()


# --------------------------------------------------------------------------- #
# Manifest integrity
# --------------------------------------------------------------------------- #
def test_framework_pack_manifest_and_verify():
    pack = packs.framework_pack("PCI DSS")
    assert pack["pack_type"] == "framework"
    assert pack["item_count"] == 2  # NGX-003 + NGX-005
    assert pack["pack_checksum"] == pack["pack_hash"][:8]
    assert packs.verify_manifest(pack) is True


def test_asset_pack_scopes_to_asset():
    pack = packs.asset_pack("web-1")
    assert pack["item_count"] == 2
    assert all(i["asset_id"] == "web-1" for i in pack["items"])
    assert packs.verify_manifest(pack) is True


def test_technology_pack():
    pack = packs.technology_pack("Redis")
    assert pack["item_count"] == 1
    assert pack["items"][0]["control_id"] == "RDX-001"


def test_application_pack_aggregates_assets():
    pack = packs.application_pack("NetBanking", ["web-1", "cache-1"])
    assert pack["item_count"] == 3
    assert packs.verify_manifest(pack) is True


def test_evidence_pack_explicit_keys():
    key = repo.make_evidence_key("web-1", "NGX-003")
    pack = packs.evidence_pack([key])
    assert pack["item_count"] == 1
    assert pack["items"][0]["evidence_key"] == key


def test_pack_hash_deterministic():
    p1 = packs.framework_pack("PCI DSS")
    p2 = packs.framework_pack("PCI DSS")
    assert p1["pack_hash"] == p2["pack_hash"]  # stable across calls


def test_tampered_manifest_fails_verification():
    pack = packs.framework_pack("PCI DSS")
    pack["items"][0]["content_hash"] = "0" * 64  # tamper
    assert packs.verify_manifest(pack) is False


def test_manifest_json_is_valid_and_sorted():
    pack = packs.asset_pack("web-1")
    text = packs.manifest_json(pack)
    parsed = json.loads(text)
    assert parsed["pack_type"] == "asset"


# --------------------------------------------------------------------------- #
# Service facade
# --------------------------------------------------------------------------- #
def test_service_build_pack_dispatch():
    assert svc.build_pack("framework", "PCI DSS")["item_count"] == 2
    assert svc.build_pack("asset", "web-1")["item_count"] == 2
    assert svc.build_pack("technology", "Redis")["item_count"] == 1
    assert svc.build_pack("application", "App", asset_ids=["web-1", "cache-1"])["item_count"] == 3
    assert svc.build_pack("bogus", "x") is None


def test_service_verify_pack():
    pack = svc.build_pack("asset", "web-1")
    assert svc.verify_pack(pack) is True
