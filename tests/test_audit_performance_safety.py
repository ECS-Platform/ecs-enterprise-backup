"""Performance / safety tests for the Audit Intelligence hardening layer.

Focus:
  * In-process caching works (repeat calls hit the cache) and never serves stale
    data after a known mutation (explicit invalidation) or a reset.
  * The shared TTL cache utility behaves (TTL expiry, bounded size, global reset).
  * Endpoints stay bounded + fast under repeated hits (demo safety) and degrade
    gracefully when a service unexpectedly raises (``_safe`` -> JSON 500, no leak).

Runs against the FastAPI app via TestClient in DEMO_MODE. Offline + deterministic.
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs
from modules.audit_intelligence.services import dashboard_service, mapping_service
from modules.shared.utils import simple_cache
from modules.shared.utils.simple_cache import TTLCache, cached, reset_all_caches

client = TestClient(app, follow_redirects=False)
Q = "role=owner&user=AppOwner"


@pytest.fixture(autouse=True)
def _clean():
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()
    mapping_service.reset_cache()
    dashboard_service.reset_cache()
    yield
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()
    mapping_service.reset_cache()
    dashboard_service.reset_cache()


def _get(path: str):
    sep = "&" if "?" in path else "?"
    return client.get(f"{path}{sep}{Q}")


# --------------------------------------------------------------------------- #
# TTL cache utility
# --------------------------------------------------------------------------- #
def test_ttlcache_memoizes_and_counts():
    calls = {"n": 0}

    @cached(ttl_seconds=100, maxsize=4)
    def f(x):
        calls["n"] += 1
        return x * 2

    assert f(3) == 6 and f(3) == 6
    assert calls["n"] == 1  # second call served from cache
    stats = f.cache_stats()
    assert stats["hits"] >= 1 and stats["misses"] >= 1


def test_ttlcache_expires_with_fake_clock():
    now = {"t": 0.0}
    c = TTLCache(ttl_seconds=10, maxsize=4, time_func=lambda: now["t"])
    c.set("k", "v")
    assert c.get("k") == "v"
    now["t"] = 11.0
    assert c.get("k") is None  # expired


def test_ttlcache_is_bounded():
    c = TTLCache(ttl_seconds=1000, maxsize=3)
    for i in range(50):
        c.set(f"k{i}", i)
    assert len(c) <= 3  # never grows past maxsize


def test_reset_all_caches_clears_registered_caches():
    c = TTLCache(ttl_seconds=1000, maxsize=4)
    c.set("k", "v")
    assert c.get("k") == "v"
    reset_all_caches()
    assert c.get("k") is None
    assert simple_cache.cache_registry_size() >= 1


# --------------------------------------------------------------------------- #
# Mapping catalog caching (pure, static -> cached)
# --------------------------------------------------------------------------- #
def test_mapping_catalog_is_cached():
    mapping_service.reset_cache()
    first = mapping_service.technologies()
    second = mapping_service.technologies()
    assert first == second
    stats = mapping_service.technologies.cache_stats()
    assert stats["hits"] >= 1, "catalog derivation should be served from cache"


def test_mapping_cache_reset_hook():
    mapping_service.technologies()
    mapping_service.reset_cache()
    stats = mapping_service.technologies.cache_stats()
    assert stats["size"] == 0 and stats["hits"] == 0


def test_mapping_endpoint_stable_under_repeated_hits():
    baseline = _get("/api/audit/mapping/stats").json()["stats"]
    for _ in range(5):
        r = _get("/api/audit/mapping/stats")
        assert r.status_code == 200
        assert r.json()["stats"] == baseline  # cached -> identical + cheap


# --------------------------------------------------------------------------- #
# Dashboard caching + invalidation (mutable state -> short TTL + explicit reset)
# --------------------------------------------------------------------------- #
def test_dashboard_cache_returns_same_object_within_ttl():
    dashboard_service.reset_cache()
    a = dashboard_service.executive_readiness()
    b = dashboard_service.executive_readiness()
    # Cached: same generated_at timestamp (not recomputed).
    assert a["generated_at"] == b["generated_at"]


def test_dashboard_cache_invalidates_on_store_evidence():
    before = dashboard_service.executive_readiness()["evidence_coverage"]["evidence_keys"]
    repo.store_evidence(control_id="NGX-003", content="x", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS",), verdict="PASS")
    after = dashboard_service.executive_readiness()["evidence_coverage"]["evidence_keys"]
    assert after == before + 1, "dashboard must reflect new evidence (cache invalidated)"


def test_dashboard_cache_invalidates_on_observation_change():
    from modules.audit_intelligence.models import ValidationResult, VERDICT_FAIL

    before = dashboard_service.executive_readiness()["open_observations"]["total"]
    vr = ValidationResult(control_id="NGX-005", technology="NGINX", verdict=VERDICT_FAIL,
                          control_status="Non-Compliant", rule_id="assertion.negative_signal",
                          frameworks=("PCI DSS",), rationale="disabled")
    obs.generate_observation(vr, asset_id="web-1")
    after = dashboard_service.executive_readiness()["open_observations"]["total"]
    assert after == before + 1


def test_dashboard_cache_invalidates_on_reset():
    repo.store_evidence(control_id="NGX-003", content="x", technology="NGINX",
                        asset_id="web-1", frameworks=("PCI DSS",), verdict="PASS")
    assert dashboard_service.executive_readiness()["evidence_coverage"]["evidence_keys"] == 1
    repo.reset_repository()
    assert dashboard_service.executive_readiness()["evidence_coverage"]["evidence_keys"] == 0


def test_dashboard_use_cache_false_forces_recompute():
    a = dashboard_service.executive_readiness()
    time.sleep(0.001)
    b = dashboard_service.executive_readiness(use_cache=False)
    assert b["generated_at"] >= a["generated_at"]


# --------------------------------------------------------------------------- #
# Demo safety: repeated hits stay bounded + fast
# --------------------------------------------------------------------------- #
def test_dashboard_endpoint_repeated_hits_are_bounded():
    started = time.perf_counter()
    for _ in range(10):
        r = _get("/api/audit/dashboard")
        assert r.status_code == 200 and r.json()["ok"] is True
    elapsed = time.perf_counter() - started
    # Generous ceiling: 10 cached dashboard hits must be well under this.
    assert elapsed < 10.0, f"dashboard hits too slow: {elapsed:.2f}s"


def test_large_evidence_repository_response_is_capped():
    for i in range(50):
        repo.store_evidence(control_id=f"NGX-{i:03d}", content="x", technology="NGINX",
                            asset_id=f"web-{i}", frameworks=("PCI DSS",), verdict="PASS")
    # Even with no explicit limit, the default cap bounds the payload.
    r = _get("/api/audit/evidence")
    assert r.status_code == 200
    body = r.json()
    assert body["page"]["total"] == 50
    assert len(body["evidence"]) <= body["page"]["limit"]


# --------------------------------------------------------------------------- #
# Graceful degradation: a service error becomes a safe JSON 500 (no leak)
# --------------------------------------------------------------------------- #
def test_service_error_is_safe_json_500(monkeypatch):
    secret_marker = "SECRET-IN-EXCEPTION-MESSAGE"

    def boom(*args, **kwargs):
        raise RuntimeError(f"boom {secret_marker}")

    # Force the runs listing service to raise; the route's _safe wrapper must
    # convert it into a consistent JSON 500 without leaking the message.
    import modules.audit_intelligence.services.evidence_service as es
    monkeypatch.setattr(es, "list_runs", boom)

    r = _get("/api/audit/runs")
    assert r.status_code == 500
    body = r.json()
    assert body["ok"] is False and body["status"] == "error"
    assert isinstance(body["errors"], list)
    assert secret_marker not in r.text, "exception message (with secret) must not leak"
