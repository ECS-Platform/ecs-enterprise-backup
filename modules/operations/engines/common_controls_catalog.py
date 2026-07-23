"""Phase-1 Common Control Library catalog — deterministic MVP definitions.

Maps each approved common control to existing predefined query IDs and an
alternate folder-based collection path under ``CommonControls/``. Controls are
framework-independent; FCM frameworks reference them via domain mapping
(see :mod:`modules.frameworks.services.common_controls_service`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Phase-1 FCM catalogue frameworks — common controls are reused across all.
FCM_FRAMEWORK_IDS: tuple[str, ...] = (
    "itpp",
    "asst",
    "mbss",
    "pci_dss",
    "dpsc",
    "csite",
    "vapt",
    "os_baseline",
    "middleware_baseline",
    "database_baseline",
)

FCM_FRAMEWORK_NAMES: tuple[str, ...] = (
    "ITPP",
    "ASST",
    "MBSS",
    "PCI DSS",
    "DPSC",
    "C-SITE",
    "VAPT",
    "OS Baseline",
    "Middleware Baseline",
    "Database Baseline",
)


@dataclass(frozen=True)
class CommonControlDef:
    name: str
    slug: str
    predefined_query_ids: tuple[str, ...]
    alternate_collection: str
    match_domains: tuple[str, ...]
    frameworks: tuple[str, ...] = FCM_FRAMEWORK_NAMES
    technology: str = "Common Control"
    control_id_prefix: str = "CC"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "predefined_query_ids": list(self.predefined_query_ids),
            "alternate_collection": self.alternate_collection,
            "frameworks": list(self.frameworks),
            "match_domains": list(self.match_domains),
            "technology": self.technology,
            "control_id": self.control_id,
            "framework_independent": True,
        }

    @property
    def control_id(self) -> str:
        return f"{self.control_id_prefix}-{self.slug.upper().replace('-', '_')}"


COMMON_CONTROLS: tuple[CommonControlDef, ...] = (
    CommonControlDef(
        name="Encryption in Transit",
        slug="encryption-in-transit",
        predefined_query_ids=("DB-001", "PGX-001", "NGX-003", "PCI-004", "MW-001"),
        alternate_collection="Bash (openssl s_client) + folder mock",
        match_domains=("Cryptography", "Encryption", "Network"),
    ),
    CommonControlDef(
        name="Encryption at Rest",
        slug="encryption-at-rest",
        predefined_query_ids=("DB-004", "PGX-002", "ORX-003", "ORX-009"),
        alternate_collection="SQL + folder mock",
        match_domains=("Cryptography", "Encryption"),
    ),
    CommonControlDef(
        name="Certificate Management",
        slug="certificate-management",
        predefined_query_ids=("MW-002",),
        alternate_collection="Scanner report + folder mock",
        match_domains=("Cryptography", "Encryption"),
    ),
    CommonControlDef(
        name="Identity & Privileged Access",
        slug="identity-privileged-access",
        predefined_query_ids=("DB-002", "PGX-004", "PCI-003", "LNX-005", "LNX-007", "LNX-008"),
        alternate_collection="SQL + PowerShell + folder mock",
        match_domains=("Access Control", "Access", "Identity"),
    ),
    CommonControlDef(
        name="Secure Configuration",
        slug="secure-configuration",
        predefined_query_ids=("OS-002", "LNX-005", "LNX-006", "NGX-005"),
        alternate_collection="Bash + folder mock",
        match_domains=("Hardening", "Integrity", "Configuration"),
    ),
    CommonControlDef(
        name="Audit Logging",
        slug="audit-logging",
        predefined_query_ids=("PGX-008", "RH8-005", "RH9-005", "PCI-002", "DB-005"),
        alternate_collection="Bash + SQL + folder mock",
        match_domains=("Monitoring", "Logging", "Audit"),
    ),
    CommonControlDef(
        name="Vulnerability & Patch",
        slug="vulnerability-patch",
        predefined_query_ids=("OS-001", "OS-006", "RH8-008", "APP-002"),
        alternate_collection="Bash + Scanner report + folder mock",
        match_domains=("Vulnerability", "Patch"),
    ),
    CommonControlDef(
        name="Backup & Restore",
        slug="backup-restore",
        predefined_query_ids=("DB-003", "PGX-003", "ASX-010", "ITPP-001", "RDX-002"),
        alternate_collection="SQL + Bash + folder mock",
        match_domains=("Backup", "Resilience"),
    ),
    CommonControlDef(
        name="Time Synchronization",
        slug="time-synchronization",
        predefined_query_ids=("OS-003",),
        alternate_collection="Bash (timedatectl) + folder mock",
        match_domains=("Operations", "Monitoring", "Patch"),
    ),
    CommonControlDef(
        name="Network Security",
        slug="network-security",
        predefined_query_ids=("LNX-004", "RH8-004", "RH9-004", "K8X-007"),
        alternate_collection="Bash + folder mock",
        match_domains=("Network",),
    ),
)


def by_slug(slug: str) -> CommonControlDef | None:
    key = (slug or "").strip().lower()
    for ctrl in COMMON_CONTROLS:
        if ctrl.slug == key:
            return ctrl
    return None


def common_controls_for_query_id(query_id: str) -> tuple[CommonControlDef, ...]:
    """Return common-control definitions that reuse this predefined query id."""
    qid = (query_id or "").strip()
    if not qid:
        return ()
    return tuple(c for c in COMMON_CONTROLS if qid in c.predefined_query_ids)


def all_slugs() -> tuple[str, ...]:
    return tuple(c.slug for c in COMMON_CONTROLS)
