"""Authentication / RBAC / security / concurrency structures.

RBAC expectations come from config/test_data.yaml (``rbac_expectations``), which are derived from ECS source
(modules/shared/services/role_permissions.py). The helper fires the SAME request as each persona and returns the
responses for ``assert_role_access``. Security probes (unauthorised manipulation) and concurrency runs are only
STRUCTURES here: they are gated by feature flags and perform nothing destructive.
"""

from __future__ import annotations

import concurrent.futures as cf
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .api_client import ApiResponse, EcsApiClient
from .assertions import assert_denied, assert_role_access
from .errors import CapabilityBlocked


class RbacHelper:
    def __init__(self, api: EcsApiClient) -> None:
        self.api = api

    def expectation(self, capability: str) -> Mapping[str, list[str]]:
        exp = self.api.cfg.test_data.get("rbac_expectations", {}).get(capability)
        if not exp:
            raise CapabilityBlocked(f"No RBAC expectation '{capability}' in config/test_data.yaml (derive it from ECS source).")
        return exp

    def as_each(self, personas: list[str], send: Callable[[EcsApiClient], ApiResponse]) -> dict[str, ApiResponse]:
        """Send the same request as every persona. ``send`` receives a persona-bound client."""
        return {p: send(self.api.as_persona(p)) for p in personas}

    def check_capability(self, capability: str, send: Callable[[EcsApiClient], ApiResponse]) -> dict[str, ApiResponse]:
        exp = self.expectation(capability)
        results = self.as_each(list(exp["allowed"]) + list(exp["denied"]), send)
        assert_role_access(results, allowed=exp["allowed"], denied=exp["denied"], msg=f"capability '{capability}'")
        return results

    def visible_to(self, path: str, personas: list[str], **params: Any) -> dict[str, ApiResponse]:
        return self.as_each(personas, lambda c: c.get(path, params=params))

    def segregation(self, path: str, personas: list[str], extract: Callable[[ApiResponse], set], **params: Any) -> dict[str, set]:
        """Per-persona visible id-set for data-segregation comparisons (e.g. enterprise vs application scope)."""
        return {p: extract(r) for p, r in self.visible_to(path, personas, **params).items()}

    def login_redirect(self, persona: str) -> ApiResponse:
        return self.api.as_persona(persona).login()


class SecurityHelper:
    """Structures for security-typed cases. Probes only run when ``security_tests`` is enabled."""

    def __init__(self, api: EcsApiClient, db=None) -> None:
        self.api, self.db = api, db

    def require_enabled(self) -> None:
        if not self.api.cfg.feature("security_tests"):
            raise CapabilityBlocked("Security probes disabled (set ECS_FT_ALLOW_SECURITY_PROBES=true on a non-production ECS).",
                                    requires="security_tests flag")

    def anonymous_request(self, method: str, path: str, **kw: Any) -> ApiResponse:
        """No identity at all. In bearer mode ECS must answer 401; in demo mode ECS passes everything through (documented)."""
        return self.api.request(method, path, anonymous=True, **kw)

    def assert_auth_enforced(self, path: str = "/api/evidence/repository") -> None:
        if (self.api.cfg.get("auth.mode") or "demo") == "demo":
            raise CapabilityBlocked("ECS runs with DEMO_MODE/ECS_LOCAL_AUTH_BYPASS: authentication is intentionally bypassed. "
                                    "Run against a bearer-auth environment (ECS_FT_AUTH_MODE=bearer).", requires="auth enabled")
        r = self.anonymous_request("GET", path)
        assert r.status == 401, f"anonymous GET {path} -> {r.status}, expected 401"

    def unauthorized_mutation(self, persona: str, send: Callable[[EcsApiClient], ApiResponse]) -> ApiResponse:
        self.require_enabled()
        resp = send(self.api.as_persona(persona))
        assert_denied(resp, f"persona '{persona}' must not be able to mutate")
        return resp

    def input_validation_probe(self, path: str, payload: Mapping[str, Any]) -> ApiResponse:
        """Send malformed/unexpected input; ECS must answer with a controlled error (never 500 stack traces)."""
        self.require_enabled()
        resp = self.api.post(path, json=payload)
        assert resp.status < 500 or "internal_error" in resp.text, f"unhandled server error {resp.status}: {resp.text[:200]}"
        assert "Traceback" not in resp.text, "stack trace leaked to client"
        return resp

    def secret_not_leaked(self, resp: ApiResponse, secrets: list[str]) -> None:
        for s in filter(None, secrets):
            assert s not in resp.text, "secret value present in response body"


@dataclass
class ConcurrencyResult:
    results: list[Any]
    errors: list[str]
    elapsed_ms: float


class ConcurrencyHelper:
    """Run N copies of an operation in parallel workers (functional concurrency, not load testing)."""

    def __init__(self, api: EcsApiClient) -> None:
        self.api = api

    def require_enabled(self) -> None:
        if not self.api.cfg.feature("concurrency_tests"):
            raise CapabilityBlocked("Concurrency scenarios disabled (set ECS_FT_ALLOW_CONCURRENCY=true).", requires="concurrency_tests flag")

    def run(self, operation: Callable[[int], Any], *, workers: int | None = None, repeat: int | None = None) -> ConcurrencyResult:
        self.require_enabled()
        conf = self.api.cfg.thresholds.get("concurrency", {})
        workers = workers or int(conf.get("parallel_workers", 4))
        total = workers * (repeat or int(conf.get("operations_per_worker", 3)))
        results, errors = [], []
        t0 = time.perf_counter()
        with cf.ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(operation, i) for i in range(total)]
            for f in cf.as_completed(futs):
                try:
                    results.append(f.result())
                except Exception as exc:  # noqa: BLE001 - collected for the assertion
                    errors.append(f"{type(exc).__name__}: {exc}")
        return ConcurrencyResult(results, errors, (time.perf_counter() - t0) * 1000.0)

    @staticmethod
    def assert_no_conflicts(res: ConcurrencyResult) -> None:
        assert not res.errors, f"{len(res.errors)} concurrent operation(s) failed: {res.errors[:3]}"
        bad = [r for r in res.results if isinstance(r, ApiResponse) and r.status >= 500]
        assert not bad, f"{len(bad)} server error(s) under concurrency: {bad[0].status} {bad[0].text[:150]}"


class PerformanceHelper:
    """Times functional calls against thresholds from config/thresholds.yaml (no load tool)."""

    def __init__(self, api: EcsApiClient) -> None:
        self.api = api

    def threshold_ms(self, key: str) -> float:
        if not self.api.cfg.feature("performance_tests"):
            raise CapabilityBlocked("Performance checks disabled (ECS_FT_ALLOW_PERFORMANCE=true).", requires="performance_tests flag")
        val = self.api.cfg.threshold(f"performance.{key}") or self.api.cfg.threshold("performance.default_response_p95_ms")
        if val is None:
            raise CapabilityBlocked(f"No SLA defined for '{key}' in config/thresholds.yaml (workbook gives none).", requires="SLA threshold")
        return float(val)

    def time_get(self, path: str, key: str = "default_response_p95_ms", **params: Any) -> ApiResponse:
        from .assertions import assert_within_ms

        limit = self.threshold_ms(key)
        resp = self.api.get(path, params=params)
        assert_within_ms(resp.elapsed_ms, limit, f"GET {path}")
        return resp
