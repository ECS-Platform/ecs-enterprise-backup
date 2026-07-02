"""Application Connectivity Readiness Assessment & Connector Certification (Phase 5.3).

A deterministic, NON-LLM onboarding framework that detects connectivity, auth,
TLS, discovery, and configuration gaps BEFORE audit execution. It performs NO
production network calls by default (offline probe), NO LLM/embeddings/RAG, and
NO connector-runtime changes. Both engines are disabled by default via
CONNECTIVITY_ASSESSMENT_ENABLED / CONNECTOR_CERTIFICATION_ENABLED.
"""

from __future__ import annotations

from app.connectivity.auth_readiness import assess_authentication
from app.connectivity.certification import (
    ConnectorCertificationEngine,
    certification_enabled,
)
from app.connectivity.discovery import assess_discovery
from app.connectivity.dns import assess_dns, is_valid_hostname
from app.connectivity.dtos import (
    AuthenticationReadinessCard,
    ConnectivityReadinessCard,
    ConnectorCertificationCard,
    DashboardWidget,
    EvidenceDiscoveryCard,
    NetworkAssessmentCard,
    build_dashboard_widgets,
)
from app.connectivity.engine import (
    ConnectivityAssessmentEngine,
    assess_connectivity,
    assessment_enabled,
)
from app.connectivity.models import (
    AuthenticationReadiness,
    AuthType,
    CertificateAssessment,
    CertificationStatus,
    CheckResult,
    ConfigurationReadiness,
    ConnectivityAssessment,
    ConnectivityProfile,
    ConnectivityType,
    ConnectorCertification,
    DNSAssessment,
    Environment,
    EvidenceDiscoveryReadiness,
    HostingType,
    NetworkAssessment,
    Outcome,
    ReadinessScore,
    ReadinessStatus,
    RiskClassification,
    RiskLevel,
)
from app.connectivity.network import assess_network, default_port_for, protocol_for
from app.connectivity.probes import DEFAULT_PROBE, OfflineProbe
from app.connectivity.scoring import calculate_readiness, classify_risk
from app.connectivity.tls import assess_tls

__all__ = [
    # enums
    "Outcome", "HostingType", "Environment", "ConnectivityType", "AuthType",
    "ReadinessStatus", "CertificationStatus", "RiskLevel",
    # models
    "ConnectivityProfile", "ConnectivityAssessment", "DNSAssessment",
    "NetworkAssessment", "CertificateAssessment", "AuthenticationReadiness",
    "EvidenceDiscoveryReadiness", "ConfigurationReadiness", "CheckResult",
    "ReadinessScore", "RiskClassification", "ConnectorCertification",
    # engines / functions
    "ConnectivityAssessmentEngine", "assess_connectivity", "assessment_enabled",
    "ConnectorCertificationEngine", "certification_enabled",
    "assess_dns", "is_valid_hostname", "assess_network", "default_port_for",
    "protocol_for", "assess_tls", "assess_authentication", "assess_discovery",
    "calculate_readiness", "classify_risk",
    # probes
    "OfflineProbe", "DEFAULT_PROBE",
    # DTOs
    "ConnectivityReadinessCard", "ConnectorCertificationCard",
    "AuthenticationReadinessCard", "EvidenceDiscoveryCard", "NetworkAssessmentCard",
    "DashboardWidget", "build_dashboard_widgets",
]
