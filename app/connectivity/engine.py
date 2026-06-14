"""ConnectivityAssessmentEngine (Phase 5.3).

Orchestrates the deterministic, non-LLM connectivity readiness assessment:
DNS, network, TLS, authentication readiness, evidence discovery, and connector
configuration — then computes a weighted readiness score and risk classification.

  * READ-ONLY      : never mutates ECS state, connectors, DB, RAG, or workflow.
  * NO-LLM         : pure deterministic logic.
  * NO NETWORK     : uses the OFFLINE probe by default; live probing is opt-in by
                     a caller injecting a probe. ECS wires no live probe here.
  * FLAG-GATED     : disabled by default (CONNECTIVITY_ASSESSMENT_ENABLED). When
                     disabled, assess_connectivity() returns a neutral disabled
                     result and performs no assessment.
  * FAIL-SAFE      : never raises into callers.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Mapping

from app.connectivity.auth_readiness import assess_authentication
from app.connectivity.discovery import assess_discovery
from app.connectivity.dns import assess_dns
from app.connectivity.models import (
    CheckResult,
    ConfigurationReadiness,
    ConnectivityAssessment,
    ConnectivityProfile,
    Outcome,
)
from app.connectivity.network import assess_network, default_port_for
from app.connectivity.probes import DEFAULT_PROBE
from app.connectivity.scoring import (
    calculate_readiness,
    classify_risk,
    connectivity_category_score,
)
from app.connectivity.tls import assess_tls

_TRUTHY = {"1", "true", "yes", "on"}


def _env_flag(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    return raw.strip().lower() in _TRUTHY


def _load_policy() -> dict[str, Any]:
    try:
        from ecs_platform.config.loader import load_config

        cfg = load_config("connectivity") or {}
        block = cfg.get("connectivity", cfg)
        return block if isinstance(block, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def assessment_enabled() -> bool:
    """Master gate. Env CONNECTIVITY_ASSESSMENT_ENABLED wins; else config; else False."""
    env = _env_flag("CONNECTIVITY_ASSESSMENT_ENABLED")
    if env is not None:
        return env
    val = _load_policy().get("assessment_enabled", False)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in _TRUTHY
    return False


def _host_from_profile(profile: ConnectivityProfile) -> str:
    if profile.host:
        return profile.host.strip()
    # Derive host from base_url if present (strip scheme/path/port).
    url = (profile.base_url or "").strip()
    if not url:
        return ""
    rest = url.split("://", 1)[-1]
    host = rest.split("/", 1)[0]
    host = host.split("@", 1)[-1]   # strip userinfo
    host = host.split(":", 1)[0]    # strip port
    return host


class ConnectivityAssessmentEngine:
    """Deterministic connectivity readiness engine."""

    def __init__(self, policy: Mapping[str, Any] | None = None,
                 *, dns_probe=None, port_probe=None, tls_probe=None) -> None:
        self.policy = dict(policy) if policy is not None else _load_policy()
        # Default to the OFFLINE probe (no network). Callers may inject live probes.
        self.dns_probe = dns_probe or DEFAULT_PROBE
        self.port_probe = port_probe or DEFAULT_PROBE
        self.tls_probe = tls_probe or DEFAULT_PROBE

    # ---------------------------------------------------------- configuration --
    def _assess_configuration(self, profile: ConnectivityProfile) -> ConfigurationReadiness:
        checks: list[CheckResult] = []

        host = _host_from_profile(profile)
        checks.append(CheckResult(
            "host_or_base_url",
            Outcome.PASS if (host or profile.base_url) else Outcome.FAIL,
            "host or base_url present" if (host or profile.base_url) else "no host/base_url"))

        ctype = profile.connectivity_type
        ctype_val = getattr(ctype, "value", str(ctype))
        net_required = ctype_val.strip().lower() not in ("agent", "manual upload", "manual_upload")
        port = profile.port or default_port_for(ctype_val)
        if net_required:
            checks.append(CheckResult(
                "port_configured",
                Outcome.PASS if port and 0 < port <= 65535 else Outcome.FAIL,
                f"port={port}"))
        else:
            checks.append(CheckResult("port_configured", Outcome.PASS,
                                      f"{ctype_val}: port not required"))

        checks.append(CheckResult(
            "connector_type",
            Outcome.PASS if profile.connector_type else Outcome.WARNING,
            profile.connector_type or "no connector type"))

        checks.append(CheckResult(
            "auth_type",
            Outcome.PASS if profile.auth_type else Outcome.FAIL,
            getattr(profile.auth_type, "value", str(profile.auth_type))))

        fails = sum(1 for c in checks if c.outcome == Outcome.FAIL)
        warns = sum(1 for c in checks if c.outcome == Outcome.WARNING)
        passes = sum(1 for c in checks if c.outcome == Outcome.PASS)
        total = len(checks) or 1
        score = round(100.0 * (passes + 0.6 * warns) / total, 1)
        if fails:
            outcome = Outcome.FAIL
        elif warns:
            outcome = Outcome.WARNING
        else:
            outcome = Outcome.PASS
        detail = f"{passes} pass, {warns} warn, {fails} fail"
        return ConfigurationReadiness(outcome=outcome, checks=checks, score=score, detail=detail)

    # ---------------------------------------------------------------- assess --
    def assess_connectivity(self, profile: ConnectivityProfile, *,
                            now: datetime | None = None, force: bool = False
                            ) -> ConnectivityAssessment:
        """Run the full deterministic assessment for one profile. Never raises."""
        app_name = getattr(profile, "application_name", "") or ""
        connector_type = getattr(profile, "connector_type", "") or ""

        if not force and not assessment_enabled():
            return ConnectivityAssessment(
                application_name=app_name, connector_type=connector_type, enabled=False,
                note="connectivity assessment disabled (CONNECTIVITY_ASSESSMENT_ENABLED=false)")

        try:
            now = now or datetime.now(timezone.utc)
            tls_cfg = self.policy.get("tls", {}) if isinstance(self.policy, Mapping) else {}
            warn_days = int(tls_cfg.get("warn_within_days", 30))
            min_tls = str(tls_cfg.get("min_tls_version", "1.2"))

            host = _host_from_profile(profile)
            ctype = profile.connectivity_type
            ctype_val = getattr(ctype, "value", str(ctype))
            port = profile.port or default_port_for(ctype_val)

            dns = assess_dns(host, probe=self.dns_probe)
            network = assess_network(host, port, ctype_val, probe=self.port_probe)
            tls = assess_tls(host, port if port else 443, warn_within_days=warn_days,
                             min_tls_version=min_tls, now=now, probe=self.tls_probe)

            auth_reqs = self.policy.get("auth_requirements") if isinstance(self.policy, Mapping) else None
            authentication = assess_authentication(
                profile.auth_type, profile.auth_config, requirements=auth_reqs)

            caps = self.policy.get("discovery_capabilities") if isinstance(self.policy, Mapping) else None
            discovery = assess_discovery(connector_type, profile.collect, capabilities=caps)

            configuration = self._assess_configuration(profile)

            # Category scores for the weighted readiness model.
            conn_score = connectivity_category_score(dns.outcome, network.outcome)
            tls_score = {Outcome.PASS: 100.0, Outcome.WARNING: 60.0,
                         Outcome.FAIL: 0.0, Outcome.UNKNOWN: 50.0}[tls.outcome]
            category_scores = {
                "connectivity": conn_score,
                "authentication": authentication.score,
                "tls": tls_score,
                "discovery": discovery.score,
                "configuration": configuration.score,
            }

            scoring_cfg = self.policy.get("scoring", {}) if isinstance(self.policy, Mapping) else {}
            readiness = calculate_readiness(
                category_scores,
                weights=scoring_cfg.get("weights"),
                bands=scoring_cfg.get("bands"))

            risk = classify_risk(
                category_scores,
                risk_config=self.policy.get("risk") if isinstance(self.policy, Mapping) else None)

            return ConnectivityAssessment(
                application_name=app_name, connector_type=connector_type, enabled=True,
                dns=dns, network=network, tls=tls, authentication=authentication,
                discovery=discovery, configuration=configuration,
                readiness=readiness, risk=risk)
        except Exception as exc:  # noqa: BLE001 - fail safe
            return ConnectivityAssessment(
                application_name=app_name, connector_type=connector_type, enabled=False,
                note=f"connectivity assessment error (ignored): {type(exc).__name__}")


def assess_connectivity(profile: ConnectivityProfile, *, now: datetime | None = None,
                        force: bool = False, **kwargs) -> ConnectivityAssessment:
    """Module-level convenience wrapper around ConnectivityAssessmentEngine."""
    return ConnectivityAssessmentEngine(**kwargs).assess_connectivity(
        profile, now=now, force=force)
