"""Scenario profiles for the ECS GCP capacity-sizing benchmark.

Each profile is a realistic deployment scale described purely as data (workload
drivers). The sizing engine (``sizing.py``) turns a profile into GKE / Cloud SQL /
GCS / logging estimates. Profiles are assumptions, not measurements — tune them
per engagement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class CapacityProfile:
    """One deployment-scale scenario (workload drivers only — no infra output)."""

    key: str
    name: str
    description: str

    # Scale
    apps: int
    frameworks: int
    controls_per_app: int
    evidences_per_app: int

    # Daily activity
    connector_runs_per_day: int
    prompt_runs_per_day: int
    api_requests_per_day: int
    scheduler_jobs_per_day: int
    concurrent_users: int

    # Sizes / retention
    avg_evidence_size_kb: float = 250.0
    evidence_versions_per_year: float = 3.0
    retention_years: int = 5

    # Growth (net-new content that becomes RAG vectors)
    new_evidence_per_app_per_month: int = 20

    def total_controls(self) -> int:
        return self.apps * self.controls_per_app

    def total_evidences(self) -> int:
        return self.apps * self.evidences_per_app

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_controls"] = self.total_controls()
        d["total_evidences"] = self.total_evidences()
        return d


# --------------------------------------------------------------------------- #
# Built-in profiles (demo -> large enterprise). Numbers are documented, tunable
# assumptions calibrated to ECS's phase model (NB/MB/Payments -> pan-bank).
# --------------------------------------------------------------------------- #
_PROFILE_LIST: list[CapacityProfile] = [
    CapacityProfile(
        key="laptop",
        name="Developer Laptop",
        description="Single developer workstation; in-memory demo, no managed services.",
        apps=1, frameworks=2, controls_per_app=40, evidences_per_app=20,
        connector_runs_per_day=5, prompt_runs_per_day=10, api_requests_per_day=200,
        scheduler_jobs_per_day=2, concurrent_users=1,
        avg_evidence_size_kb=150.0, evidence_versions_per_year=1.0, retention_years=1,
        new_evidence_per_app_per_month=5,
    ),
    CapacityProfile(
        key="pilot",
        name="Pilot",
        description="Small pilot on managed services ahead of Phase 1.",
        apps=2, frameworks=4, controls_per_app=100, evidences_per_app=120,
        connector_runs_per_day=30, prompt_runs_per_day=40, api_requests_per_day=2000,
        scheduler_jobs_per_day=15, concurrent_users=10,
        avg_evidence_size_kb=250.0, evidence_versions_per_year=2.0, retention_years=3,
        new_evidence_per_app_per_month=20,
    ),
    CapacityProfile(
        key="demo",
        name="Demo / Local",
        description="Single-laptop demo/prototype; in-memory or one small DB.",
        apps=3, frameworks=3, controls_per_app=40, evidences_per_app=30,
        connector_runs_per_day=10, prompt_runs_per_day=20, api_requests_per_day=500,
        scheduler_jobs_per_day=5, concurrent_users=2,
        avg_evidence_size_kb=200.0, evidence_versions_per_year=2.0, retention_years=1,
        new_evidence_per_app_per_month=10,
    ),
    CapacityProfile(
        key="phase1",
        name="Phase 1 — NB / MB / Payments",
        description="Three flagship banking applications (Net Banking, Mobile Banking, Payments).",
        apps=3, frameworks=6, controls_per_app=120, evidences_per_app=200,
        connector_runs_per_day=60, prompt_runs_per_day=80, api_requests_per_day=5000,
        scheduler_jobs_per_day=30, concurrent_users=25,
        avg_evidence_size_kb=250.0, evidence_versions_per_year=3.0, retention_years=5,
        new_evidence_per_app_per_month=25,
    ),
    CapacityProfile(
        key="phase2",
        name="Phase 2 — 15 applications",
        description="Departmental rollout across 15 applications.",
        apps=15, frameworks=8, controls_per_app=120, evidences_per_app=180,
        connector_runs_per_day=200, prompt_runs_per_day=250, api_requests_per_day=20000,
        scheduler_jobs_per_day=120, concurrent_users=75,
        avg_evidence_size_kb=250.0, evidence_versions_per_year=3.0, retention_years=5,
        new_evidence_per_app_per_month=25,
    ),
    CapacityProfile(
        key="apps25",
        name="25 applications",
        description="Multi-department rollout across 25 applications.",
        apps=25, frameworks=8, controls_per_app=120, evidences_per_app=170,
        connector_runs_per_day=320, prompt_runs_per_day=400, api_requests_per_day=32000,
        scheduler_jobs_per_day=200, concurrent_users=100,
        avg_evidence_size_kb=280.0, evidence_versions_per_year=3.0, retention_years=5,
        new_evidence_per_app_per_month=22,
    ),
    CapacityProfile(
        key="apps50",
        name="50 applications",
        description="Division-wide rollout across 50 applications.",
        apps=50, frameworks=9, controls_per_app=120, evidences_per_app=160,
        connector_runs_per_day=620, prompt_runs_per_day=750, api_requests_per_day=64000,
        scheduler_jobs_per_day=420, concurrent_users=180,
        avg_evidence_size_kb=290.0, evidence_versions_per_year=3.0, retention_years=5,
        new_evidence_per_app_per_month=21,
    ),
    CapacityProfile(
        key="enterprise",
        name="Enterprise — 100 applications",
        description="Enterprise-wide GRC across ~100 applications.",
        apps=100, frameworks=10, controls_per_app=120, evidences_per_app=150,
        connector_runs_per_day=1200, prompt_runs_per_day=1500, api_requests_per_day=120000,
        scheduler_jobs_per_day=800, concurrent_users=300,
        avg_evidence_size_kb=300.0, evidence_versions_per_year=3.0, retention_years=5,
        new_evidence_per_app_per_month=20,
    ),
    CapacityProfile(
        key="apps250",
        name="250 applications",
        description="Large multi-entity rollout across 250 applications.",
        apps=250, frameworks=11, controls_per_app=120, evidences_per_app=145,
        connector_runs_per_day=3000, prompt_runs_per_day=3200, api_requests_per_day=280000,
        scheduler_jobs_per_day=2000, concurrent_users=600,
        avg_evidence_size_kb=300.0, evidence_versions_per_year=3.0, retention_years=7,
        new_evidence_per_app_per_month=20,
    ),
    CapacityProfile(
        key="pan-bank",
        name="Pan-Bank — 500 applications",
        description="Bank-wide deployment across ~500 applications / business units.",
        apps=500, frameworks=12, controls_per_app=120, evidences_per_app=140,
        connector_runs_per_day=6000, prompt_runs_per_day=6000, api_requests_per_day=500000,
        scheduler_jobs_per_day=4000, concurrent_users=1000,
        avg_evidence_size_kb=300.0, evidence_versions_per_year=3.0, retention_years=7,
        new_evidence_per_app_per_month=20,
    ),
    CapacityProfile(
        key="apps1000",
        name="1000 applications",
        description="Very large estate across 1000 applications.",
        apps=1000, frameworks=14, controls_per_app=120, evidences_per_app=130,
        connector_runs_per_day=12000, prompt_runs_per_day=11000, api_requests_per_day=1000000,
        scheduler_jobs_per_day=8000, concurrent_users=2000,
        avg_evidence_size_kb=330.0, evidence_versions_per_year=4.0, retention_years=7,
        new_evidence_per_app_per_month=20,
    ),
    CapacityProfile(
        key="large",
        name="Large Enterprise — 2000 applications",
        description="Very large / multi-entity estate (~2000 applications).",
        apps=2000, frameworks=15, controls_per_app=120, evidences_per_app=120,
        connector_runs_per_day=24000, prompt_runs_per_day=20000, api_requests_per_day=2000000,
        scheduler_jobs_per_day=16000, concurrent_users=3000,
        avg_evidence_size_kb=350.0, evidence_versions_per_year=4.0, retention_years=7,
        new_evidence_per_app_per_month=20,
    ),
]

#: Profiles keyed by their ``key``.
PROFILES: dict[str, CapacityProfile] = {p.key: p for p in _PROFILE_LIST}


def list_profiles() -> list[str]:
    """Ordered profile keys (demo -> large)."""
    return [p.key for p in _PROFILE_LIST]


def get_profile(key: str) -> CapacityProfile:
    """Look up a profile by key; raises KeyError with the valid set on miss."""
    try:
        return PROFILES[key]
    except KeyError:
        raise KeyError(
            f"Unknown capacity profile '{key}'. Valid: {', '.join(list_profiles())}"
        ) from None
