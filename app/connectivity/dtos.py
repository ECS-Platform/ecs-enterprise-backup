"""Onboarding & dashboard DTOs (Phase 5.3).

Reusable, presentation-ready objects built FROM a ConnectivityAssessment. These
are pure data-transfer objects — they perform no I/O and do NOT modify any
existing dashboard. They exist so a future UI can render connectivity/certification
/risk widgets without recomputing anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.connectivity.certification import ConnectorCertificationEngine
from app.connectivity.models import (
    CertificationStatus,
    ConnectivityAssessment,
    ConnectorCertification,
    Outcome,
    ReadinessStatus,
    RiskLevel,
)


def _val(v: Any) -> Any:
    return getattr(v, "value", v)


@dataclass
class NetworkAssessmentCard:
    application_name: str = ""
    dns: dict[str, Any] = field(default_factory=dict)
    network: dict[str, Any] = field(default_factory=dict)
    tls: dict[str, Any] = field(default_factory=dict)
    overall: str = Outcome.UNKNOWN.value

    @classmethod
    def from_assessment(cls, a: ConnectivityAssessment) -> "NetworkAssessmentCard":
        outcomes = [a.dns.outcome, a.network.outcome, a.tls.outcome]
        if Outcome.FAIL in outcomes:
            overall = Outcome.FAIL
        elif Outcome.WARNING in outcomes:
            overall = Outcome.WARNING
        elif all(o == Outcome.UNKNOWN for o in outcomes):
            overall = Outcome.UNKNOWN
        else:
            overall = Outcome.PASS
        return cls(application_name=a.application_name, dns=a.dns.to_dict(),
                   network=a.network.to_dict(), tls=a.tls.to_dict(), overall=overall.value)

    def to_dict(self) -> dict[str, Any]:
        return {"application_name": self.application_name, "dns": self.dns,
                "network": self.network, "tls": self.tls, "overall": self.overall}


@dataclass
class AuthenticationReadinessCard:
    application_name: str = ""
    auth_type: str = ""
    outcome: str = Outcome.UNKNOWN.value
    score: float = 0.0
    missing_fields: list[str] = field(default_factory=list)
    detail: str = ""

    @classmethod
    def from_assessment(cls, a: ConnectivityAssessment) -> "AuthenticationReadinessCard":
        au = a.authentication
        return cls(application_name=a.application_name, auth_type=au.auth_type,
                   outcome=_val(au.outcome), score=au.score,
                   missing_fields=list(au.missing_fields), detail=au.detail)

    def to_dict(self) -> dict[str, Any]:
        return {"application_name": self.application_name, "auth_type": self.auth_type,
                "outcome": self.outcome, "score": self.score,
                "missing_fields": self.missing_fields, "detail": self.detail}


@dataclass
class EvidenceDiscoveryCard:
    application_name: str = ""
    connector_type: str = ""
    outcome: str = Outcome.UNKNOWN.value
    score: float = 0.0
    discoverable_categories: list[str] = field(default_factory=list)
    unsupported_categories: list[str] = field(default_factory=list)

    @classmethod
    def from_assessment(cls, a: ConnectivityAssessment) -> "EvidenceDiscoveryCard":
        d = a.discovery
        return cls(application_name=a.application_name, connector_type=d.connector_type,
                   outcome=_val(d.outcome), score=d.score,
                   discoverable_categories=list(d.discoverable_categories),
                   unsupported_categories=list(d.unsupported_categories))

    def to_dict(self) -> dict[str, Any]:
        return {"application_name": self.application_name, "connector_type": self.connector_type,
                "outcome": self.outcome, "score": self.score,
                "discoverable_categories": self.discoverable_categories,
                "unsupported_categories": self.unsupported_categories}


@dataclass
class ConnectivityReadinessCard:
    application_name: str = ""
    connector_type: str = ""
    enabled: bool = False
    readiness_score: float = 0.0
    status: str = ReadinessStatus.RED.value
    risk_level: str = RiskLevel.LOW.value
    category_scores: dict[str, float] = field(default_factory=dict)
    note: str = ""

    @classmethod
    def from_assessment(cls, a: ConnectivityAssessment) -> "ConnectivityReadinessCard":
        return cls(application_name=a.application_name, connector_type=a.connector_type,
                   enabled=a.enabled, readiness_score=a.readiness.score,
                   status=_val(a.readiness.status), risk_level=_val(a.risk.level),
                   category_scores=dict(a.readiness.category_scores), note=a.note)

    def to_dict(self) -> dict[str, Any]:
        return {"application_name": self.application_name, "connector_type": self.connector_type,
                "enabled": self.enabled, "readiness_score": self.readiness_score,
                "status": self.status, "risk_level": self.risk_level,
                "category_scores": self.category_scores, "note": self.note}


@dataclass
class ConnectorCertificationCard:
    application_name: str = ""
    connector_type: str = ""
    status: str = CertificationStatus.NOT_CERTIFIED.value
    score: float = 0.0
    factors: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    @classmethod
    def from_assessment(cls, a: ConnectivityAssessment, *,
                        certification: ConnectorCertification | None = None,
                        force: bool = False) -> "ConnectorCertificationCard":
        cert = certification or ConnectorCertificationEngine().certify(a, force=force)
        return cls(application_name=a.application_name, connector_type=cert.connector_type,
                   status=_val(cert.status), score=cert.score,
                   factors=dict(cert.factors), reasons=list(cert.reasons))

    def to_dict(self) -> dict[str, Any]:
        return {"application_name": self.application_name, "connector_type": self.connector_type,
                "status": self.status, "score": self.score,
                "factors": self.factors, "reasons": self.reasons}


# --------------------------------------------------------------------------- #
# Dashboard widget DTOs (data only; no rendering, no existing-dashboard changes)
# --------------------------------------------------------------------------- #

@dataclass
class DashboardWidget:
    """Generic widget descriptor for a future connectivity dashboard."""

    widget_id: str
    title: str
    kind: str                       # "gauge" | "status" | "list" | "badge"
    value: Any = None
    items: list[Any] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"widget_id": self.widget_id, "title": self.title, "kind": self.kind,
                "value": self.value, "items": list(self.items), "meta": dict(self.meta)}


def build_dashboard_widgets(assessment: ConnectivityAssessment, *,
                            force: bool = False) -> list[DashboardWidget]:
    """Build connectivity/certification/risk widgets from an assessment (data only)."""
    cert = ConnectorCertificationEngine().certify(assessment, force=force)
    return [
        DashboardWidget(
            "connectivity_readiness", "Connectivity Readiness", "gauge",
            value=assessment.readiness.score,
            meta={"status": _val(assessment.readiness.status),
                  "category_scores": dict(assessment.readiness.category_scores)}),
        DashboardWidget(
            "connector_certification", "Connector Certification", "badge",
            value=_val(cert.status),
            meta={"score": cert.score, "factors": dict(cert.factors)}),
        DashboardWidget(
            "onboarding_risk", "Onboarding Risk", "status",
            value=_val(assessment.risk.level),
            meta={"gap_score": assessment.risk.gap_score,
                  "factors": dict(assessment.risk.factors)}),
        DashboardWidget(
            "network_assessment", "Network Assessment", "list",
            items=[assessment.dns.to_dict(), assessment.network.to_dict(),
                   assessment.tls.to_dict()]),
        DashboardWidget(
            "evidence_discovery", "Evidence Discovery", "list",
            value=assessment.discovery.score,
            items=list(assessment.discovery.discoverable_categories),
            meta={"unsupported": list(assessment.discovery.unsupported_categories)}),
    ]
