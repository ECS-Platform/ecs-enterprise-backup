"""Dashboard, search/filter/drill-down, compliance and reporting capabilities (read-mostly).

Real ECS surfaces:
  Role dashboards (HTML) : /dashboard, /dashboard/{cio,vertical-head,compliance-head,functional-head}
  Pages (HTML)           : /mvp/evidence-dashboard, /mvp/enterprise, /mvp/pan-india, /mvp/trends, /mvp/comparison,
                           /mvp/reports, /mvp/audit-prep, /mvp/lifecycle, /mvp/search, /mvp/completeness
  JSON                   : /api/evidence-dashboard/{fcm-progress,phase2-leadership,fcm-drill/{fw}/{ctrl}}, /api/audit/dashboard[/{section}],
                           /api/audit/comparison, /api/evidence/completeness, /api/platform/{executive-summary,audit-readiness,evidence-reuse},
                           /api/audit/observations/summary, /api/evidence-workflow/summary, /api/framework/{kpi-drill,row-drill,tab-drill,workflow-drill},
                           /api/audit-prep/{kpi-drill,audit-detail,upcoming}
  Reports                : /mvp/reports/view/{type}, /mvp/reports/download/{id}?format=, /audit/package/{generate,export},
                           POST /mvp/comparison/export-gaps, /mvp/exports/{download,preview}/{id}
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from .api_client import ApiResponse, EcsApiClient
from .data_factory import DataFactory

ROLE_DASHBOARDS = {"cio": "/dashboard/cio", "vertical_head": "/dashboard/vertical-head",
                   "compliance_head": "/dashboard/compliance-head", "compliance_officer": "/dashboard/compliance-head",
                   "security_officer": "/dashboard/compliance-head", "functional_head": "/dashboard/functional-head",
                   "owner": "/dashboard", "auditor": "/dashboard"}


class DashboardHelper:
    def __init__(self, api: EcsApiClient, data: DataFactory) -> None:
        self.api, self.data = api, data

    # ---- role dashboards --------------------------------------------------------------------------------------
    def role_dashboard(self, persona: str) -> ApiResponse:
        return self.api.as_persona(persona).get(ROLE_DASHBOARDS.get(persona, "/dashboard"))

    def page(self, path: str, **params: str) -> ApiResponse:
        return self.api.get(path, params=params)

    # ---- JSON dashboards ---------------------------------------------------------------------------------------------
    def fcm_progress(self, application: str = "", framework_id: str = "", role: str = "") -> dict[str, Any]:
        params = {"application": application, "framework_id": framework_id}
        if role:
            params["role"] = role
        return self.api.get_json("/api/evidence-dashboard/fcm-progress", params=params)

    def leadership(self) -> dict[str, Any]:
        return self.api.get_json("/api/evidence-dashboard/phase2-leadership")

    def audit_dashboard(self, section: str = "") -> dict[str, Any]:
        return self.api.get_json(f"/api/audit/dashboard/{section}" if section else "/api/audit/dashboard")

    def executive_summary(self) -> dict[str, Any]:
        return self.api.get_json("/api/platform/executive-summary")

    def audit_readiness(self) -> dict[str, Any]:
        return self.api.get_json("/api/platform/audit-readiness")

    def completeness(self, framework: str = "All Frameworks", application: str = "All Applications", risk: str = "All Risk",
                     role: str = "owner") -> dict[str, Any]:
        return self.api.get_json("/api/evidence/completeness",
                                 params={"framework": framework, "application": application, "risk": risk, "role": role})

    def comparison(self, scope: str = "All Applications", time_range: str = "Current Month") -> dict[str, Any]:
        return self.api.get_json("/api/audit/comparison", params={"scope": scope, "time_range": time_range})

    def observations_summary(self) -> dict[str, Any]:
        return self.api.get_json("/api/audit/observations/summary")

    # ---- drill-down ----------------------------------------------------------------------------------------------------
    def fcm_drill(self, framework_id: str, control_id: str) -> dict[str, Any]:
        return self.api.get_json(f"/api/evidence-dashboard/fcm-drill/{framework_id}/{control_id}")

    def kpi_drill(self, **params: str) -> ApiResponse:
        return self.api.get("/api/framework/kpi-drill", params=params)

    def audit_prep_kpi_drill(self, **params: str) -> ApiResponse:
        return self.api.get("/api/audit-prep/kpi-drill", params=params)

    # ---- numbers helpers (reconciliation) -----------------------------------------------------------------------------
    @staticmethod
    def numbers_in(obj: Any, key_pattern: str) -> list[float]:
        """Collect numeric values for keys matching ``key_pattern`` anywhere in a JSON structure."""
        pat = re.compile(key_pattern, re.I)
        out: list[float] = []

        def walk(o: Any) -> None:
            if isinstance(o, dict):
                for k, v in o.items():
                    if pat.search(str(k)) and isinstance(v, (int, float)) and not isinstance(v, bool):
                        out.append(float(v))
                    else:
                        walk(v)
            elif isinstance(o, list):
                for i in o:
                    walk(i)

        walk(obj)
        return out

    def kpi_values(self, body: Any) -> dict[str, Any]:
        """Flatten top-level scalar KPIs from a dashboard payload for comparison before/after an action."""
        flat: dict[str, Any] = {}

        def walk(o: Any, prefix: str = "") -> None:
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, f"{prefix}{k}.")
            elif isinstance(o, (int, float, str, bool)) and prefix:
                flat[prefix[:-1]] = o

        walk(body)
        return flat


class SearchHelper:
    """Search / filter / sort / drill-down over ECS list endpoints."""

    def __init__(self, api: EcsApiClient) -> None:
        self.api = api

    def rows(self, path: str, **params: Any) -> list[dict]:
        from .evidence import _items

        resp = self.api.get(path, params={k: v for k, v in params.items() if v not in (None, "")})
        return _items(resp.json()) if resp.status == 200 and resp.is_json else []

    def evidence(self, q: str = "", **filters: str) -> list[dict]:
        return self.rows("/api/evidence/search", q=q, **filters)

    def page(self, path: str, **params: Any) -> ApiResponse:
        """HTML list page with ECS's standard filters (q, framework, application, status, sort...)."""
        return self.api.get(path, params={k: v for k, v in params.items() if v not in (None, "")})

    def predefined_queries(self, control_id: str = "") -> ApiResponse:
        return self.api.get(f"/api/predefined-queries/{control_id}") if control_id else self.api.get("/mvp/predefined-queries")

    def common_controls(self) -> Any:
        return self.api.get_json("/api/common-controls")

    def common_control(self, slug: str) -> ApiResponse:
        return self.api.get(f"/api/common-controls/{slug}")

    def framework_controls(self, framework_id: str) -> ApiResponse:
        return self.api.get(f"/api/framework-control-master/frameworks/{framework_id}")

    def control_master_search(self, q: str, **filters: str) -> ApiResponse:
        return self.api.get("/api/framework-control-master/search", params={"q": q, **filters})

    @staticmethod
    def is_sorted(values: Iterable[Any], reverse: bool = False) -> bool:
        vals = list(values)
        return vals == sorted(vals, reverse=reverse)


class ComplianceHelper:
    """Framework / control / mapping / applicability / validation."""

    def __init__(self, api: EcsApiClient, data: DataFactory) -> None:
        self.api, self.data = api, data

    def frameworks(self) -> ApiResponse:
        return self.api.get("/api/framework-control-master/frameworks")

    def framework(self, framework_id: str) -> ApiResponse:
        return self.api.get(f"/api/framework-control-master/frameworks/{framework_id}")

    def control(self, framework_id: str, control_id: str) -> ApiResponse:
        return self.api.get(f"/api/framework-control-master/controls/{framework_id}/{control_id}")

    def common_controls(self) -> ApiResponse:
        return self.api.get("/api/common-controls")

    def common_controls_for_framework(self, framework_id: str) -> ApiResponse:
        return self.api.get(f"/api/common-controls/framework/{framework_id}")

    def validate_completeness(self, **scope: str) -> ApiResponse:
        """POST /api/evidence-reuse/validate-completeness (application, framework, control, technology, status, full_catalog)."""
        return self.api.post("/api/evidence-reuse/validate-completeness", params=scope)

    def readiness(self, **scope: str) -> ApiResponse:
        return self.api.get("/api/evidence-reuse/readiness", params=scope)

    def generate_observations(self, **scope: str) -> ApiResponse:
        return self.api.post("/api/evidence-reuse/generate-observations", params=scope)

    def check_closure(self, **scope: str) -> ApiResponse:
        return self.api.post("/api/evidence-reuse/check-closure", params=scope)

    def run_validation(self, run_id: str) -> ApiResponse:
        return self.api.get(f"/api/audit/runs/{run_id}/validation")

    def start_run(self, scope_kind: str, **payload: Any) -> ApiResponse:
        return self.api.post("/api/audit/runs", json={"scope_kind": scope_kind, **payload})

    def mapping_stats(self) -> ApiResponse:
        return self.api.get("/api/audit/mapping/stats")

    def import_framework(self, payload: dict[str, Any], persona: str = "compliance_head") -> ApiResponse:
        return self.api.as_persona(persona).post("/api/framework-onboarding/import", json=payload)


class ReportingHelper:
    def __init__(self, api: EcsApiClient, data: DataFactory) -> None:
        self.api, self.data = api, data

    def catalog(self) -> ApiResponse:
        return self.api.get("/mvp/reports")

    def view(self, report_type: str) -> ApiResponse:
        return self.api.get(f"/mvp/reports/view/{report_type}")

    def download(self, report_id: str, fmt: str = "pdf", persona: str | None = None, **scope: str) -> ApiResponse:
        client = self.api.as_persona(persona) if persona else self.api
        return client.get(f"/mvp/reports/download/{report_id}", params={
            "format": fmt, "framework": scope.get("framework", self.data.framework()),
            "application": scope.get("application", self.data.application())})

    def generate_audit_package(self, persona: str = "cio") -> ApiResponse:
        return self.api.as_persona(persona).post("/audit/package/generate", headers={"X-Requested-With": "XMLHttpRequest"})

    def export_audit_package(self, **params: str) -> ApiResponse:
        return self.api.get("/audit/package/export", params=params)

    def export_comparison_gaps(self, **form: str) -> ApiResponse:
        return self.api.post("/mvp/comparison/export-gaps", data=form)

    def audit_prep(self) -> ApiResponse:
        return self.api.get("/mvp/audit-prep")

    def deterministic(self, report_id: str, fmt: str = "csv", **scope: str) -> bool:
        """Two consecutive downloads of the same report with the same parameters yield identical bytes."""
        a = self.download(report_id, fmt, **scope)
        b = self.download(report_id, fmt, **scope)
        return a.status == b.status == 200 and a.content == b.content
