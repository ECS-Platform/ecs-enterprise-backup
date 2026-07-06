"""Tests for the in-process TTL cache + audit-intelligence performance safeguards.

Covers: TTL cache correctness/expiry/eviction/reset, mapping_service caching +
invalidation, in-memory store caps, pagination, and a large-mocked-inventory
performance sanity check. Deterministic and offline.
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.shared.utils.simple_cache import TTLCache, cached, reset_all_caches


# --------------------------------------------------------------------------- #
# TTL cache
# --------------------------------------------------------------------------- #
def test_cache_hit_and_miss():
    clock = {"t": 1000.0}
    c = TTLCache(ttl_seconds=10, maxsize=8, time_func=lambda: clock["t"])
    assert c.get("k", "default") == "default"
    c.set("k", "v")
    assert c.get("k") == "v"
    assert c.stats()["hits"] == 1 and c.stats()["misses"] == 1


def test_cache_ttl_expiry():
    clock = {"t": 0.0}
    c = TTLCache(ttl_seconds=5, time_func=lambda: clock["t"])
    c.set("k", "v")
    clock["t"] = 4.9
    assert c.get("k") == "v"        # still live
    clock["t"] = 5.1
    assert c.get("k") is None        # expired


def test_cache_maxsize_eviction():
    clock = {"t": 0.0}
    c = TTLCache(ttl_seconds=100, maxsize=2, time_func=lambda: clock["t"])
    c.set("a", 1); c.set("b", 2); c.set("c", 3)  # evicts one
    assert len(c) == 2


def test_get_or_set_computes_once():
    calls = {"n": 0}
    c = TTLCache(ttl_seconds=100)

    def factory():
        calls["n"] += 1
        return 42

    assert c.get_or_set("k", factory) == 42
    assert c.get_or_set("k", factory) == 42
    assert calls["n"] == 1  # cached second time


def test_cached_decorator_and_clear():
    calls = {"n": 0}

    @cached(ttl_seconds=100, maxsize=4)
    def f(x):
        calls["n"] += 1
        return x * 2

    assert f(3) == 6 and f(3) == 6
    assert calls["n"] == 1
    f.cache_clear()
    assert f(3) == 6
    assert calls["n"] == 2  # recomputed after clear


def test_reset_all_caches():
    @cached()
    def g():
        return object()

    v1 = g()
    assert g() is v1
    reset_all_caches()
    assert g() is not v1


# --------------------------------------------------------------------------- #
# mapping_service caching + invalidation
# --------------------------------------------------------------------------- #
def test_mapping_service_cache_and_invalidation():
    from modules.audit_intelligence.services import mapping_service

    mapping_service.reset_cache()
    a = mapping_service.stats()
    b = mapping_service.stats()
    assert a == b
    # technologies() is cached and returns a stable list
    t1 = mapping_service.technologies()
    t2 = mapping_service.technologies()
    assert t1 == t2 and len(t1) >= 1
    mapping_service.reset_cache()  # must not raise; next call recomputes
    assert mapping_service.stats() == a


# --------------------------------------------------------------------------- #
# In-memory store caps
# --------------------------------------------------------------------------- #
def test_repository_version_cap():
    from modules.audit_intelligence.engines import evidence_repository as repo

    repo.reset_repository()
    cap = repo.MAX_VERSIONS_PER_KEY
    for i in range(cap + 10):
        repo.store_evidence(control_id="C", content=f"v{i}", asset_id="a")
    versions = repo.get_versions(repo.make_evidence_key("a", "C"))
    assert len(versions) == cap  # capped
    repo.reset_repository()


def test_run_store_cap():
    from modules.audit_intelligence.engines import evidence_orchestrator as orch

    orch.reset_runs()
    # Create a few runs; cap is large (500), so just assert store works + bounded.
    for _ in range(5):
        orch.create_run(scope_kind="control", scope_value="NGX-001", control_ids=["NGX-001"])
    assert len(orch.list_runs()) == 5
    assert len(orch.list_runs()) <= orch.MAX_RETAINED_RUNS
    orch.reset_runs()


# --------------------------------------------------------------------------- #
# Pagination + large inventory perf sanity
# --------------------------------------------------------------------------- #
def test_api_pagination(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, follow_redirects=False)
    r = client.get("/api/audit/assets?limit=3&offset=0&role=owner&user=AppOwner")
    assert r.status_code == 200
    body = r.json()
    assert body["page"]["limit"] == 3
    assert len(body["inventory"]) <= 3
    assert "elapsed_ms" in body


def test_large_mocked_inventory_performance():
    """Fingerprinting + coverage over a large mocked inventory stays fast."""
    from modules.audit_intelligence.engines import asset_discovery
    from modules.audit_intelligence.services import asset_service

    records = [{"asset_id": f"A{i}", "hostname": f"host-{i}",
                "image": "postgres:16" if i % 2 else "nginx:1.25"} for i in range(500)]
    start = time.perf_counter()
    assets = asset_discovery.discover_from_manual(records)
    cov = asset_service.coverage_summary(assets)
    elapsed = time.perf_counter() - start
    assert len(assets) == 500
    assert cov["identified_assets"] == 500
    assert elapsed < 5.0  # generous ceiling; typically well under 1s
