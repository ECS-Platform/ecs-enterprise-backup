"""Connectivity readiness — domain models and enums (Phase 5.3).

Deterministic, non-LLM data structures for the Application Connectivity Readiness
Assessment and Connector Certification Framework. No network, DB, RAG, or LLM
imports. All dataclasses are plain, JSON-serializable via ``to_dict()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #

class Outcome(str, Enum):
    """Result of a single deterministic check."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    UNKNOWN = "UNKNOWN"   # offline / not probed -> neutral, never punitive as FAIL


class HostingType(str, Enum):
    CLOUD = "Cloud"
    DATACENTER = "Datacenter"
    HYBRID = "Hybrid"
    SAAS = "SaaS"


class Environment(str, Enum):
    DEV = "Dev"
    UAT = "UAT"
    PRODUCTION = "Production"


class ConnectivityType(str, Enum):
    REST_API = "REST API"
    SOAP_API = "SOAP API"
    DATABASE = "Database"
    FILE_SHARE = "File Share"
    AGENT = "Agent"
    MANUAL_UPLOAD = "Manual Upload"


class AuthType(str, Enum):
    OAUTH = "OAuth"
    PAT = "PAT"
    SERVICE_ACCOUNT = "Service Account"
    LDAP = "LDAP"
    KERBEROS = "Kerberos"
    SAML = "SAML"
    JWT = "JWT"


class ReadinessStatus(str, Enum):
    GREEN = "Green"
    AMBER = "Amber"
    RED = "Red"


class CertificationStatus(str, Enum):
    CERTIFIED = "Certified"
    PARTIALLY_CERTIFIED = "Partially Certified"
    NOT_CERTIFIED = "Not Certified"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


def _enum_value(v: Any) -> Any:
    return v.value if isinstance(v, Enum) else v


# --------------------------------------------------------------------------- #
# Connectivity profile (onboarding input)
# --------------------------------------------------------------------------- #

@dataclass
class ConnectivityProfile:
    """Onboarding model capturing how an application/source connects to ECS."""

    application_name: str
    hosting_type: HostingType | str = HostingType.SAAS
    environment: Environment | str = Environment.PRODUCTION
    connectivity_type: ConnectivityType | str = ConnectivityType.REST_API
    auth_type: AuthType | str = AuthType.PAT
    connector_type: str = ""              # e.g. "jira", "github" (maps to integrations.yaml)
    host: str = ""                        # hostname or DNS name (no scheme)
    port: int = 0                         # 0 -> derive from connectivity_type default
    base_url: str = ""                    # full base url if known
    # Names of env vars expected to carry credentials (mirrors integrations.yaml).
    auth_config: dict[str, str] = field(default_factory=dict)
    collect: list[str] = field(default_factory=list)  # evidence categories requested
    verify_ssl: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_name": self.application_name,
            "hosting_type": _enum_value(self.hosting_type),
            "environment": _enum_value(self.environment),
            "connectivity_type": _enum_value(self.connectivity_type),
            "auth_type": _enum_value(self.auth_type),
            "connector_type": self.connector_type,
            "host": self.host,
            "port": self.port,
            "base_url": self.base_url,
            "auth_config": dict(self.auth_config),
            "collect": list(self.collect),
            "verify_ssl": self.verify_ssl,
            "metadata": dict(self.metadata),
        }


# --------------------------------------------------------------------------- #
# Per-category assessment results
# --------------------------------------------------------------------------- #

@dataclass
class CheckResult:
    """Generic outcome of a deterministic check."""

    name: str
    outcome: Outcome = Outcome.UNKNOWN
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "outcome": _enum_value(self.outcome),
                "detail": self.detail, "data": dict(self.data)}


@dataclass
class DNSAssessment:
    hostname: str = ""
    resolved_ip: str = ""
    latency_ms: float | None = None
    outcome: Outcome = Outcome.UNKNOWN
    error_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"hostname": self.hostname, "resolved_ip": self.resolved_ip,
                "latency_ms": self.latency_ms, "outcome": _enum_value(self.outcome),
                "error_reason": self.error_reason}


@dataclass
class NetworkAssessment:
    host: str = ""
    port: int = 0
    protocol: str = ""
    outcome: Outcome = Outcome.UNKNOWN
    latency_ms: float | None = None
    error_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"host": self.host, "port": self.port, "protocol": self.protocol,
                "outcome": _enum_value(self.outcome), "latency_ms": self.latency_ms,
                "error_reason": self.error_reason}


@dataclass
class CertificateAssessment:
    host: str = ""
    present: bool = False
    expires_at: str = ""
    days_to_expiry: int | None = None
    chain_valid: bool | None = None
    cipher: str = ""
    tls_version: str = ""
    outcome: Outcome = Outcome.UNKNOWN
    error_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"host": self.host, "present": self.present, "expires_at": self.expires_at,
                "days_to_expiry": self.days_to_expiry, "chain_valid": self.chain_valid,
                "cipher": self.cipher, "tls_version": self.tls_version,
                "outcome": _enum_value(self.outcome), "error_reason": self.error_reason}


@dataclass
class AuthenticationReadiness:
    auth_type: str = ""
    outcome: Outcome = Outcome.UNKNOWN
    required_fields: list[str] = field(default_factory=list)
    present_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    score: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"auth_type": self.auth_type, "outcome": _enum_value(self.outcome),
                "required_fields": list(self.required_fields),
                "present_fields": list(self.present_fields),
                "missing_fields": list(self.missing_fields),
                "score": self.score, "detail": self.detail}


@dataclass
class EvidenceDiscoveryReadiness:
    connector_type: str = ""
    outcome: Outcome = Outcome.UNKNOWN
    supported_categories: list[str] = field(default_factory=list)
    requested_categories: list[str] = field(default_factory=list)
    discoverable_categories: list[str] = field(default_factory=list)
    unsupported_categories: list[str] = field(default_factory=list)
    score: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"connector_type": self.connector_type, "outcome": _enum_value(self.outcome),
                "supported_categories": list(self.supported_categories),
                "requested_categories": list(self.requested_categories),
                "discoverable_categories": list(self.discoverable_categories),
                "unsupported_categories": list(self.unsupported_categories),
                "score": self.score, "detail": self.detail}


@dataclass
class ConfigurationReadiness:
    outcome: Outcome = Outcome.UNKNOWN
    checks: list[CheckResult] = field(default_factory=list)
    score: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"outcome": _enum_value(self.outcome),
                "checks": [c.to_dict() for c in self.checks],
                "score": self.score, "detail": self.detail}


# --------------------------------------------------------------------------- #
# Scoring / certification / risk
# --------------------------------------------------------------------------- #

@dataclass
class ReadinessScore:
    score: float = 0.0
    status: ReadinessStatus | str = ReadinessStatus.RED
    category_scores: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "status": _enum_value(self.status),
                "category_scores": dict(self.category_scores),
                "weights": dict(self.weights)}


@dataclass
class RiskClassification:
    level: RiskLevel | str = RiskLevel.LOW
    gap_score: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"level": _enum_value(self.level), "gap_score": self.gap_score,
                "factors": dict(self.factors), "reasons": list(self.reasons)}


@dataclass
class ConnectorCertification:
    connector_type: str = ""
    status: CertificationStatus | str = CertificationStatus.NOT_CERTIFIED
    score: float = 0.0
    factors: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"connector_type": self.connector_type, "status": _enum_value(self.status),
                "score": self.score, "factors": dict(self.factors),
                "reasons": list(self.reasons)}


@dataclass
class ConnectivityAssessment:
    """The full deterministic assessment for one connectivity profile."""

    application_name: str = ""
    connector_type: str = ""
    enabled: bool = False
    dns: DNSAssessment = field(default_factory=DNSAssessment)
    network: NetworkAssessment = field(default_factory=NetworkAssessment)
    tls: CertificateAssessment = field(default_factory=CertificateAssessment)
    authentication: AuthenticationReadiness = field(default_factory=AuthenticationReadiness)
    discovery: EvidenceDiscoveryReadiness = field(default_factory=EvidenceDiscoveryReadiness)
    configuration: ConfigurationReadiness = field(default_factory=ConfigurationReadiness)
    readiness: ReadinessScore = field(default_factory=ReadinessScore)
    risk: RiskClassification = field(default_factory=RiskClassification)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_name": self.application_name,
            "connector_type": self.connector_type,
            "enabled": self.enabled,
            "dns": self.dns.to_dict(),
            "network": self.network.to_dict(),
            "tls": self.tls.to_dict(),
            "authentication": self.authentication.to_dict(),
            "discovery": self.discovery.to_dict(),
            "configuration": self.configuration.to_dict(),
            "readiness": self.readiness.to_dict(),
            "risk": self.risk.to_dict(),
            "note": self.note,
        }
