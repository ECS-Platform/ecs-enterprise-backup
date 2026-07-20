"""Phase-1 Common Control Library catalog — deterministic MVP definitions.

Maps each approved common control to existing predefined query IDs and an
alternate folder-based collection path under ``CommonControls/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FW = (
    "PCI DSS",
    "DPSC",
    "ISG Baseline",
    "ISO 27001",
    "VAPT",
    "IS",
    "CSITE",
)


@dataclass(frozen=True)
class CommonControlDef:
    name: str
    slug: str
    predefined_query_ids: tuple[str, ...]
    alternate_collection: str
    frameworks: tuple[str, ...] = FW
    technology: str = "Common Control"
    control_id_prefix: str = "CC"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "predefined_query_ids": list(self.predefined_query_ids),
            "alternate_collection": self.alternate_collection,
            "frameworks": list(self.frameworks),
            "technology": self.technology,
            "control_id": self.control_id,
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
    ),
    CommonControlDef(
        name="Encryption at Rest",
        slug="encryption-at-rest",
        predefined_query_ids=("DB-004", "PGX-002", "ORX-003", "ORX-009"),
        alternate_collection="SQL + folder mock",
    ),
    CommonControlDef(
        name="Certificate Management",
        slug="certificate-management",
        predefined_query_ids=("MW-002",),
        alternate_collection="Scanner report + folder mock",
    ),
    CommonControlDef(
        name="Identity & Privileged Access",
        slug="identity-privileged-access",
        predefined_query_ids=("DB-002", "PGX-004", "PCI-003", "LNX-005", "LNX-007", "LNX-008"),
        alternate_collection="SQL + PowerShell + folder mock",
    ),
    CommonControlDef(
        name="Secure Configuration",
        slug="secure-configuration",
        predefined_query_ids=("OS-002", "LNX-005", "LNX-006", "NGX-005"),
        alternate_collection="Bash + folder mock",
    ),
    CommonControlDef(
        name="Audit Logging",
        slug="audit-logging",
        predefined_query_ids=("PGX-008", "RH8-005", "RH9-005", "PCI-002", "DB-005"),
        alternate_collection="Bash + SQL + folder mock",
    ),
    CommonControlDef(
        name="Vulnerability & Patch",
        slug="vulnerability-patch",
        predefined_query_ids=("OS-001", "OS-006", "RH8-008", "APP-002"),
        alternate_collection="Bash + Scanner report + folder mock",
    ),
    CommonControlDef(
        name="Backup & Restore",
        slug="backup-restore",
        predefined_query_ids=("DB-003", "PGX-003", "ASX-010", "ITPP-001", "RDX-002"),
        alternate_collection="SQL + Bash + folder mock",
    ),
    CommonControlDef(
        name="Time Synchronization",
        slug="time-synchronization",
        predefined_query_ids=("OS-003",),
        alternate_collection="Bash (timedatectl) + folder mock",
    ),
    CommonControlDef(
        name="Network Security",
        slug="network-security",
        predefined_query_ids=("LNX-004", "RH8-004", "RH9-004", "K8X-007"),
        alternate_collection="Bash + folder mock",
    ),
)


def by_slug(slug: str) -> CommonControlDef | None:
    key = (slug or "").strip().lower()
    for ctrl in COMMON_CONTROLS:
        if ctrl.slug == key:
            return ctrl
    return None


def all_slugs() -> tuple[str, ...]:
    return tuple(c.slug for c in COMMON_CONTROLS)
