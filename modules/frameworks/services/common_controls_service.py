"""Common Control Library service — catalog + FCM cross-reference (no duplicate controls)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from modules.frameworks.repositories.framework_control_repository import (
    get_framework_control_repository,
)
from modules.operations.engines.common_controls_catalog import (
    COMMON_CONTROLS,
    CommonControlDef,
    FCM_FRAMEWORK_IDS,
    FCM_FRAMEWORK_NAMES,
    by_slug,
)


class CommonControlsService:
    def list_controls(self) -> dict[str, Any]:
        return {
            "ok": True,
            "count": len(COMMON_CONTROLS),
            "frameworks": list(FCM_FRAMEWORK_NAMES),
            "controls": [c.to_dict() for c in COMMON_CONTROLS],
        }

    def get_control(self, slug: str) -> dict[str, Any]:
        ctrl = by_slug(slug)
        if ctrl is None:
            return {"ok": False, "message": f"Common control '{slug}' not found."}
        return {
            "ok": True,
            **ctrl.to_dict(),
            "framework_mappings": self.resolve_fcm_references(slug),
        }

    def resolve_fcm_references(self, slug: str) -> list[dict[str, Any]]:
        """Map a framework-independent common control to FCM policy/control/procedure/EVR refs."""
        ctrl = by_slug(slug)
        if ctrl is None:
            return []
        repo = get_framework_control_repository()
        refs: list[dict[str, Any]] = []
        domains = {d.lower() for d in ctrl.match_domains}
        for fw_id in FCM_FRAMEWORK_IDS:
            doc = repo.get_framework(fw_id) or {}
            fw = doc.get("framework") or {}
            fw_name = str(fw.get("name") or fw.get("display_name") or fw_id)
            for control in doc.get("controls") or []:
                domain = str(control.get("domain") or "")
                if domain.lower() not in domains and not any(
                    d in domain.lower() for d in domains
                ):
                    continue
                refs.append(
                    {
                        "common_control_id": ctrl.control_id,
                        "common_control_slug": ctrl.slug,
                        "common_control_name": ctrl.name,
                        "framework_id": fw_id,
                        "framework_name": fw_name,
                        "policy_refs": list(control.get("policy_refs") or []),
                        "control_id": control.get("id"),
                        "control_title": control.get("title"),
                        "domain": domain,
                        "procedure_ids": [
                            p.get("id") for p in (control.get("procedures") or []) if p.get("id")
                        ],
                        "evidence_requirement_ids": [
                            e.get("id")
                            for e in (control.get("evidence_requirements") or [])
                            if e.get("id")
                        ],
                    }
                )
        return refs

    def controls_for_framework(self, framework_id: str) -> list[dict[str, Any]]:
        fw_key = (framework_id or "").strip().lower()
        out: list[dict[str, Any]] = []
        for ctrl in COMMON_CONTROLS:
            mappings = [
                m
                for m in self.resolve_fcm_references(ctrl.slug)
                if m.get("framework_id") == fw_key
                or str(m.get("framework_name", "")).lower() == fw_key
            ]
            if mappings:
                out.append({**ctrl.to_dict(), "fcm_references": mappings})
        return out

    def dashboard_summary(self) -> dict[str, Any]:
        collected = 0
        try:
            from modules.shared.services.evidence_authoritative_reader import (
                collect_authoritative_evidence_rows,
            )

            collected = sum(
                1
                for row in collect_authoritative_evidence_rows()
                if row.get("source_connector") == "common_controls"
                or (row.get("metadata") or {}).get("collection_source") == "CommonControls"
            )
        except Exception:  # noqa: BLE001
            collected = 0
        return {
            "catalog_count": len(COMMON_CONTROLS),
            "frameworks_supported": len(FCM_FRAMEWORK_IDS),
            "persisted_evidence_count": collected,
            "framework_independent": True,
        }


@lru_cache(maxsize=1)
def get_common_controls_service() -> CommonControlsService:
    return CommonControlsService()
