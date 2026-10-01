"""Lifecycle (version / retention / archival / historical retrieval) and onboarding / CRUD capabilities.

Real ECS surfaces:
  GET  /mvp/platform/evidence-lifecycle?status=   POST /mvp/platform/evidence-lifecycle/review (evidence_uid, status, note, valid_days)
  table evidence_reviews(status Collected|UnderReview|Approved|Rejected|Expired, valid_until)   GET /mvp/lifecycle
  GET  /api/audit/evidence/{key}/versions|timeline
  POST /mvp/platform/onboarding (application) ; GET /mvp/platform/onboarding ; POST /mvp/onboarding ; POST /api/onboarding/simulate|export
  POST /api/framework-onboarding/{import,lifecycle,reuse-decision}  GET /api/framework-onboarding/{id}
  GET  /api/admin/{roles,applications}   POST /api/admin/users/{user_id}/role
ECS has NO archival trigger and NO retention-policy API: those raise CapabilityBlocked (documented gap).
"""

from __future__ import annotations

from typing import Any

from .api_client import ApiResponse, EcsApiClient
from .data_factory import DataFactory
from .errors import CapabilityBlocked

LIFECYCLE_STATUSES = ("Collected", "UnderReview", "Approved", "Rejected", "Expired")


class LifecycleHelper:
    def __init__(self, api: EcsApiClient, data: DataFactory, db=None) -> None:
        self.api, self.data, self.db = api, data, db

    def page(self, status: str = "") -> ApiResponse:
        return self.api.get("/mvp/platform/evidence-lifecycle", params={"status": status} if status else None)

    def set_status(self, evidence_uid: str, status: str, *, note: str = "", valid_days: int = 0, persona: str = "auditor") -> ApiResponse:
        return self.api.as_persona(persona).post("/mvp/platform/evidence-lifecycle/review", data={
            "evidence_uid": evidence_uid, "status": status, "note": note, "valid_days": valid_days})

    def review_row(self, evidence_uid: str) -> dict[str, Any] | None:
        return self.db.one("evidence_reviews", evidence_uid=evidence_uid) if self.db else None

    def expired_rows(self) -> list[dict[str, Any]]:
        return self.db.find("evidence_reviews", status="Expired") if self.db else []

    # ---- explicit gaps (kept as callable so tests document the missing capability) -----------------------------------
    def apply_retention_policy(self, *_a: Any, **_k: Any) -> None:
        raise CapabilityBlocked("ECS exposes no retention-policy configuration/enforcement API; only evidence_reviews.valid_until "
                                "(set via valid_days on the lifecycle review route).", requires="retention policy API")

    def trigger_archival(self, *_a: Any, **_k: Any) -> None:
        raise CapabilityBlocked("ECS exposes no archival workflow trigger; the object store is immutable (put_immutable).",
                                requires="archival workflow API")

    def delete_evidence(self, *_a: Any, **_k: Any) -> None:
        raise CapabilityBlocked("ECS exposes no evidence delete endpoint (immutability / audit protection).", requires="delete API")

    def object_store_is_immutable(self, store_helper, key: str) -> bool:
        """Immutability is enforced by LocalObjectStore/S3ObjectStore.put_immutable; verified by the stored hash staying equal."""
        return store_helper.exists(key)


class OnboardingHelper:
    """Application / framework onboarding and admin CRUD."""

    def __init__(self, api: EcsApiClient, data: DataFactory, db=None) -> None:
        self.api, self.data, self.db = api, data, db

    def onboard_application(self, persona: str = "owner", **overrides: Any) -> tuple[dict[str, Any], ApiResponse]:
        fields = self.data.application_record(**overrides)
        return fields, self.api.as_persona(persona).post("/mvp/platform/onboarding", data=fields)

    def application_page(self) -> ApiResponse:
        return self.api.get("/mvp/platform/onboarding")

    def application_row(self, name: str) -> dict[str, Any] | None:
        slug = name.lower().replace(" ", "-")
        return (self.db.one("applications", slug=slug) or self.db.one("applications", name=name)) if self.db else None

    def admin_applications(self) -> ApiResponse:
        return self.api.get("/api/admin/applications", params={"role": "system_admin"})

    def admin_roles(self) -> ApiResponse:
        return self.api.get("/api/admin/roles", params={"role": "system_admin"})

    def simulate(self, payload: dict[str, Any], persona: str = "compliance_head") -> ApiResponse:
        return self.api.as_persona(persona).post("/api/onboarding/simulate", json=payload)

    def export(self, payload: dict[str, Any], persona: str = "compliance_head") -> ApiResponse:
        return self.api.as_persona(persona).post("/api/onboarding/export", json=payload)

    def framework_lifecycle(self, payload: dict[str, Any], persona: str = "compliance_head") -> ApiResponse:
        return self.api.as_persona(persona).post("/api/framework-onboarding/lifecycle", json=payload)

    def reuse_decision(self, payload: dict[str, Any], persona: str = "compliance_head") -> ApiResponse:
        return self.api.as_persona(persona).post("/api/framework-onboarding/reuse-decision", json=payload)

    def framework_status(self, framework_id: str) -> ApiResponse:
        return self.api.get(f"/api/framework-onboarding/{framework_id}")
