"""Framework Control Master service — presentation layer over the repository.

Routes and dashboard templates must call this service only. Storage backends
(file catalogue, database, Excel, SharePoint, upload pipeline) are selected
via the injected :class:`FrameworkControlRepository` implementation.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from modules.frameworks.repositories.framework_control_repository import (
    FrameworkControlRepository,
    get_framework_control_repository,
)


class FrameworkControlMasterService:
    def __init__(self, repository: FrameworkControlRepository | None = None) -> None:
        self._repo = repository or get_framework_control_repository()

    @property
    def source_type(self) -> str:
        return self._repo.source_type()

    def list_frameworks(self) -> dict[str, Any]:
        rows = self._repo.list_framework_summaries()
        return {
            "ok": True,
            "source_type": self.source_type,
            "frameworks": rows,
            "stats": self._repo.catalog_stats(),
        }

    def get_framework_detail(self, framework_id: str) -> dict[str, Any]:
        doc = self._repo.get_framework(framework_id)
        if not doc:
            return {"ok": False, "message": f"Framework '{framework_id}' not found."}
        return {"ok": True, "source_type": self.source_type, **doc}

    def get_control_detail(self, framework_id: str, control_id: str) -> dict[str, Any]:
        doc = self._repo.get_control(framework_id, control_id)
        if not doc:
            return {
                "ok": False,
                "message": f"Control '{control_id}' not found in framework '{framework_id}'.",
            }
        return {"ok": True, "source_type": self.source_type, **doc}

    def search_controls(
        self,
        query: str = "",
        framework_id: str = "",
        domain: str = "",
    ) -> dict[str, Any]:
        rows = self._repo.search_controls(
            query=query,
            framework_id=framework_id or None,
            domain=domain or None,
        )
        return {
            "ok": True,
            "source_type": self.source_type,
            "query": query,
            "framework_id": framework_id,
            "domain": domain,
            "count": len(rows),
            "controls": rows,
        }

    def build_dashboard(
        self,
        role: str = "compliance_head",
        selected_framework_id: str = "",
        query: str = "",
    ) -> dict[str, Any]:
        stats = self._repo.catalog_stats()
        frameworks = self._repo.list_framework_summaries()
        selected = None
        if selected_framework_id:
            selected = self._repo.get_framework(selected_framework_id)
        if not selected and frameworks:
            selected = self._repo.get_framework(frameworks[0]["id"])
        search_results = self._repo.search_controls(query=query) if query else []
        domains: list[str] = []
        if selected:
            seen: set[str] = set()
            for ctrl in selected.get("controls") or []:
                dom = ctrl.get("domain") or ""
                if dom and dom not in seen:
                    seen.add(dom)
                    domains.append(dom)
        return {
            "role": role,
            "source_type": self.source_type,
            "catalog_version": stats.get("catalog_version", ""),
            "stats": stats,
            "frameworks": frameworks,
            "selected_framework_id": (selected or {}).get("framework", {}).get("id", ""),
            "selected": selected,
            "domains": domains,
            "search_query": query,
            "search_results": search_results,
            "kpi_cards": [
                {
                    "label": "Frameworks",
                    "value": stats.get("framework_count", 0),
                    "tone": "primary",
                },
                {
                    "label": "Policies",
                    "value": stats.get("policy_count", 0),
                    "tone": "info",
                },
                {
                    "label": "Controls",
                    "value": stats.get("control_count", 0),
                    "tone": "success",
                },
                {
                    "label": "Procedures",
                    "value": stats.get("procedure_count", 0),
                    "tone": "secondary",
                },
                {
                    "label": "Evidence Requirements",
                    "value": stats.get("evidence_requirement_count", 0),
                    "tone": "warning",
                },
                {
                    "label": "Catalog Source",
                    "value": self.source_type.upper(),
                    "tone": "dark",
                },
            ],
        }


    def build_evidence_dashboard_progress(
        self,
        role: str = "owner",
        application: str = "",
        framework_id: str = "",
    ) -> dict[str, Any]:
        from modules.governance.engines.fcm_evidence_progress_engine import (
            build_framework_progress,
        )

        return build_framework_progress(
            self._repo,
            role=role,
            application=application,
            framework_id=framework_id,
        )

    def build_evidence_progress_drill(
        self,
        framework_id: str,
        control_id: str,
        application: str = "",
        role: str = "",
    ) -> dict[str, Any]:
        from modules.governance.engines.fcm_evidence_progress_engine import (
            build_evidence_drill,
        )

        return build_evidence_drill(
            self._repo,
            framework_id=framework_id,
            control_id=control_id,
            application=application,
            role=role,
        )

    def list_assigned_applications(self, role: str = "owner") -> list[str]:
        from modules.governance.engines.fcm_evidence_progress_engine import (
            _applications_for_role,
        )

        return _applications_for_role(role, self._repo)


@lru_cache(maxsize=1)
def get_framework_control_master_service() -> FrameworkControlMasterService:
    return FrameworkControlMasterService()
