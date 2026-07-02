"""Connector certification engine (Phase 5.3).

Deterministically certifies a connector based on four factors derived from a
ConnectivityAssessment: Connectivity, Authentication, Discovery, Configuration.

Outcome:
  * Certified           — high composite score and no hard-gate failures.
  * Partially Certified — moderate score / recoverable gaps.
  * Not Certified       — low score or a hard-gate failure (auth/config FAIL).
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from app.connectivity.models import (
    CertificationStatus,
    ConnectivityAssessment,
    ConnectorCertification,
    Outcome,
)

_TRUTHY = {"1", "true", "yes", "on"}

DEFAULT_CERT = {
    "certified_min": 85,
    "partially_certified_min": 55,
    "hard_fail_categories": ["authentication", "configuration"],
}


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


def certification_enabled() -> bool:
    """Master gate for certification. Env CONNECTOR_CERTIFICATION_ENABLED wins."""
    env = _env_flag("CONNECTOR_CERTIFICATION_ENABLED")
    if env is not None:
        return env
    val = _load_policy().get("certification_enabled", False)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in _TRUTHY
    return False


class ConnectorCertificationEngine:
    """Stateless deterministic certification engine."""

    def __init__(self, policy: Mapping[str, Any] | None = None) -> None:
        cert = {**DEFAULT_CERT}
        source = policy if policy is not None else _load_policy().get("certification", {})
        if isinstance(source, Mapping):
            cert.update(source)
        self.cert = cert

    def certify(self, assessment: ConnectivityAssessment, *, force: bool = False
                ) -> ConnectorCertification:
        """Certify a connector from its assessment. Never raises."""
        if not force and not certification_enabled():
            return ConnectorCertification(
                connector_type=getattr(assessment, "connector_type", ""),
                status=CertificationStatus.NOT_CERTIFIED, score=0.0,
                reasons=["certification engine disabled (CONNECTOR_CERTIFICATION_ENABLED=false)"])
        try:
            cats = assessment.readiness.category_scores or {}
            connectivity = float(cats.get("connectivity", 0.0))
            authentication = float(cats.get("authentication", assessment.authentication.score))
            discovery = float(cats.get("discovery", assessment.discovery.score))
            configuration = float(cats.get("configuration", assessment.configuration.score))

            factors = {
                "connectivity": round(connectivity, 1),
                "authentication": round(authentication, 1),
                "discovery": round(discovery, 1),
                "configuration": round(configuration, 1),
            }
            score = round((connectivity + authentication + discovery + configuration) / 4.0, 1)

            reasons: list[str] = []
            hard_fail = False
            hard_cats = self.cert.get("hard_fail_categories", [])
            outcome_by_cat = {
                "authentication": assessment.authentication.outcome,
                "configuration": assessment.configuration.outcome,
                "discovery": assessment.discovery.outcome,
            }
            for cat in hard_cats:
                if outcome_by_cat.get(cat) == Outcome.FAIL:
                    hard_fail = True
                    reasons.append(f"hard-gate failure: {cat}")

            certified_min = float(self.cert.get("certified_min", 85))
            partial_min = float(self.cert.get("partially_certified_min", 55))

            if hard_fail:
                status = CertificationStatus.NOT_CERTIFIED
            elif score >= certified_min:
                status = CertificationStatus.CERTIFIED
                reasons.append(f"score {score} >= {certified_min}")
            elif score >= partial_min:
                status = CertificationStatus.PARTIALLY_CERTIFIED
                reasons.append(f"score {score} in [{partial_min}, {certified_min})")
            else:
                status = CertificationStatus.NOT_CERTIFIED
                reasons.append(f"score {score} < {partial_min}")

            return ConnectorCertification(
                connector_type=getattr(assessment, "connector_type", ""),
                status=status, score=score, factors=factors, reasons=reasons)
        except Exception as exc:  # noqa: BLE001 - fail safe
            return ConnectorCertification(
                connector_type=getattr(assessment, "connector_type", ""),
                status=CertificationStatus.NOT_CERTIFIED, score=0.0,
                reasons=[f"certification error (ignored): {type(exc).__name__}"])
