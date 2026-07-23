"""Predefined Queries service — REST/UI facade over the execution engine."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import predefined_query_phase1_registry as phase1
from modules.operations.engines.common_controls_catalog import common_controls_for_query_id


class PredefinedQueriesService:
    def list_controls(self, *, phase1_only: bool = True) -> dict[str, Any]:
        engine.load_predefined_queries()
        controls = engine.get_all_controls()
        if phase1_only:
            selected = phase1.phase1_selected_ids()
            controls = [c for c in controls if c.get("control_id") in selected]
        rows = []
        for c in controls:
            cid = str(c.get("control_id") or "")
            cap = engine.assess_execution_capability(c)
            rows.append(
                {
                    "control_id": cid,
                    "control_name": c.get("control_name") or cid,
                    "technology": c.get("technology") or "",
                    "frameworks": list(c.get("frameworks") or []),
                    "framework_coverage": c.get("framework_coverage") or "",
                    "executable": bool(cap.get("executable")),
                    "execution_status": cap.get("status") or "",
                    "common_control_slugs": [cc.slug for cc in common_controls_for_query_id(cid)],
                }
            )
        return {
            "ok": True,
            "phase_label": phase1.load_phase1_registry().get("phase_label", "Phase1"),
            "count": len(rows),
            "controls": rows,
        }

    def get_control(self, control_id: str) -> dict[str, Any]:
        engine.load_predefined_queries()
        control = engine.get_control_by_id(control_id)
        if not control:
            return {"ok": False, "message": f"Control '{control_id}' not found."}
        cap = engine.assess_execution_capability(control)
        return {
            "ok": True,
            "control": control,
            "capability": cap,
            "phase1_selected": phase1.is_phase1_selected(control_id),
            "common_controls": [cc.to_dict() for cc in common_controls_for_query_id(control_id)],
        }

    def resolve_mappings(self, control_id: str) -> dict[str, Any]:
        """Common Control + FCM policy/control/procedure/EVR references for a query."""
        engine.load_predefined_queries()
        control = engine.get_control_by_id(control_id)
        if not control:
            return {"ok": False, "message": f"Control '{control_id}' not found."}
        cc_refs: list[dict[str, Any]] = []
        fcm_refs: list[dict[str, Any]] = []
        try:
            from modules.frameworks.services.common_controls_service import (
                get_common_controls_service,
            )

            svc = get_common_controls_service()
            for cc in common_controls_for_query_id(control_id):
                cc_refs.append(cc.to_dict())
                fcm_refs.extend(svc.resolve_fcm_references(cc.slug))
        except Exception:  # noqa: BLE001
            pass
        try:
            from modules.audit_intelligence.engines import technology_control_mapping as tcm

            tref = tcm.get_control(control_id)
            tech_mapping = tref.to_dict() if tref else None
        except Exception:  # noqa: BLE001
            tech_mapping = None
        return {
            "ok": True,
            "control_id": control_id,
            "common_controls": cc_refs,
            "fcm_references": fcm_refs,
            "technology_control_mapping": tech_mapping,
        }


@lru_cache(maxsize=1)
def get_predefined_queries_service() -> PredefinedQueriesService:
    return PredefinedQueriesService()
