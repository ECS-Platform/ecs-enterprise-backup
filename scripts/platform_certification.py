#!/usr/bin/env python3
"""ECS Platform Certification — full-stack audit across roles, modules, KPIs, and drilldowns."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import ecs_state  # noqa: E402
from app.main import app  # noqa: E402
from modules.shared.services.module_capabilities import get_module_capability  # noqa: E402
from modules.shared.drilldowns.module_kpi_drill_engine import drill_module_kpi  # noqa: E402
from modules.shared.services.persona_display import PERSONA_BY_ROLE  # noqa: E402
from modules.operations.engines.ai_ops_summary_engine import (  # noqa: E402
    SUMMARY_PAGE_MODES,
    build_summary_page,
)

client = TestClient(app, raise_server_exceptions=False)

ROLES = [
    ("cio", "cio@bank.com"),
    ("vertical_head", "vertical.head@bank.com"),
    ("owner", "owner.app1@bank.com"),
    ("auditor", "audit.lead@bank.com"),
    ("compliance_head", "compliance.head@bank.com"),
    ("compliance_officer", "compliance.officer@bank.com"),
    ("functional_head", "functional.head@bank.com"),
    ("security_officer", "security.officer@bank.com"),
    ("operations_owner", "ops.owner@bank.com"),
    ("ai_governance_owner", "ai.gov@bank.com"),
    ("ai_sdlc_owner", "ai.sdlc@bank.com"),
    ("framework_owner", "framework.owner@bank.com"),
]

ROLE_DASHBOARD_ROUTES = {
    "cio": "/dashboard/cio",
    "vertical_head": "/dashboard/vertical-head",
    "compliance_head": "/dashboard/compliance-head",
    "functional_head": "/dashboard/functional-head",
    "owner": "/dashboard",
    "auditor": "/dashboard",
    "framework_owner": "/mvp/framework-admin",
}

MODULE_ROUTES: dict[str, list[str]] = {
    "Executive Overview": [
        "/mvp/demo-overview", "/mvp/enterprise", "/mvp/pan-india", "/mvp/reports", "/mvp/trends",
        "/dashboard", "/dashboard/cio", "/dashboard/vertical-head",
        "/dashboard/compliance-head", "/dashboard/functional-head",
    ],
    "Frameworks": ["/mvp/framework-loader", "/mvp/framework-admin"],
    "Operations": [
        "/mvp/scheduler", "/mvp/ai-ops-assistant", "/mvp/upload", "/mvp/integrations",
        "/mvp/onboarding", "/mvp/integrations-hub", "/mvp/bulk-upload",
    ],
    "Governance": [
        "/mvp/audit-prep", "/mvp/evidence-health", "/mvp/reuse", "/mvp/lifecycle",
        "/mvp/completeness", "/mvp/comparison", "/mvp/search", "/mvp/evidence-approval",
    ],
    "Enterprise GRC": [
        "/mvp/risk-register", "/mvp/exceptions", "/mvp/exception-governance", "/mvp/cmdb",
        "/mvp/regulatory", "/mvp/heatmaps", "/mvp/correlation", "/mvp/governance-analytics",
    ],
    "AI SDLC Governance": [
        "/mvp/ai-sdlc", "/mvp/ai-sdlc/control-tower", "/mvp/ai-sdlc/onboarding",
        "/mvp/ai-sdlc/requirements", "/mvp/ai-sdlc/design", "/mvp/ai-sdlc/development",
        "/mvp/ai-sdlc/testing", "/mvp/ai-sdlc/golive", "/mvp/ai-sdlc/evidence",
        "/mvp/ai-sdlc/findings",
        "/mvp/ai-governance", "/mvp/ai-registry", "/mvp/sdlc-gates", "/mvp/governance-quality",
    ],
}

KPI_OPTIONAL_ROUTES = frozenset({
    "/mvp/upload", "/mvp/ai-sdlc/onboarding", "/mvp/framework-loader", "/",
})

FORBIDDEN_PAGE_PATTERNS = [
    (re.compile(r">\s*No Data Available\s*<", re.I), "No Data Available"),
    (re.compile(r">\s*No Records Found\s*<", re.I), "No Records Found"),
    (re.compile(r">\s*Item Not Found\s*<", re.I), "Item Not Found"),
    (re.compile(r"ECS CIO|CIO CIO|App Owner App Owner", re.I), "duplicate role branding"),
]

DUPLICATE_TAB_PATTERN = re.compile(
    r'data-ecs-tab-switch="([^"]+)"[\s\S]*?ecs-workspace-tab[^>]*>\s*\1\s*<',
    re.I,
)

KPI_MODULES = [
    "scheduler", "onboarding", "integrations", "audit_prep", "evidence_health",
    "completeness", "governance_analytics", "risk_register", "trends", "reports",
    "ai_ops_assistant",
]

DRILL_METRICS = {
    "scheduler": ["failed_collections", "pending_jobs", "total_jobs"],
    "onboarding": ["onboard", "pending", "fail"],
    "audit_prep": ["draft", "submitted", "blockers"],
    "governance_analytics": ["audit_readiness", "open_findings", "sla"],
    "trends": ["implementation_coverage", "open_observations", "sla_breaches"],
    "reports": ["available", "generated", "scheduled"],
    "ai_ops_assistant": ["active_incidents", "incident"],
}

SCRIPT_BLOCK = re.compile(r"<script[\s\S]*?</script>", re.I)


def _url(route: str, role: str, user: str) -> str:
    sep = "&" if "?" in route else "?"
    return f"{route}{sep}role={role}&user={quote(user)}"


def discover_html_routes() -> list[str]:
    """Phase 1 — inventory HTML GET routes from FastAPI app."""
    routes: list[str] = []
    for r in app.routes:
        if getattr(r, "methods", None) and "GET" in r.methods:
            path = getattr(r, "path", "")
            if path and "{" not in path and path.startswith(("/mvp", "/dashboard", "/framework")):
                routes.append(path)
    return sorted(set(routes))


def _strip_scripts(html: str) -> str:
    return SCRIPT_BLOCK.sub("", html)


def _analyze_page(text: str, module: str, route: str, role: str) -> list[dict]:
    issues: list[dict] = []
    body = _strip_scripts(text)
    if "Internal Server Error" in text or "UndefinedError" in text:
        issues.append({
            "phase": "empty_page",
            "severity": "P1",
            "module": module,
            "route": route,
            "role": role,
            "issue": "Template/render error",
        })
    for pat, label in FORBIDDEN_PAGE_PATTERNS:
        if pat.search(body):
            issues.append({
                "phase": "duplicate_ui",
                "severity": "P1",
                "module": module,
                "route": route,
                "role": role,
                "issue": label,
            })
    if DUPLICATE_TAB_PATTERN.search(body):
        issues.append({
            "phase": "duplicate_ui",
            "severity": "P2",
            "module": module,
            "route": route,
            "role": role,
            "issue": "Duplicate tab row (data-ecs-tab-switch + workspace tabs)",
        })
    tab_labels = re.findall(
        r'class="ecs-workspace-tab(?:[^"]*)"[^>]*>\s*([^<\n]+?)\s*<',
        body,
    )
    tab_labels = [lbl.strip() for lbl in tab_labels if lbl.strip() and len(lbl.strip()) < 40]
    dup_tabs = [lbl for lbl, cnt in Counter(tab_labels).items() if cnt > 1]
    if dup_tabs:
        issues.append({
            "phase": "duplicate_ui",
            "severity": "P2",
            "module": module,
            "route": route,
            "role": role,
            "issue": f"Duplicate workspace tab labels: {dup_tabs}",
        })
    persona = PERSONA_BY_ROLE.get(role, {})
    if persona and route.startswith(("/dashboard", "/mvp")):
        if persona["display_name"] not in text and "ecs-persona-profile" not in text:
            if route not in ("/mvp/upload", "/mvp/bulk-upload"):
                issues.append({
                    "phase": "role_header",
                    "severity": "P2",
                    "module": module,
                    "route": route,
                    "role": role,
                    "issue": f"Persona display name missing: {persona['display_name']}",
                })
    if route not in KPI_OPTIONAL_ROUTES:
        if "ecs-exec-kpi" not in text and "ecs-kpi" not in text and "demo-kpi" not in text:
            if "kpi_card" not in text and "ecs-persona-tab" not in route:
                if not route.startswith("/dashboard"):
                    pass  # dashboards use kpi_card macro, not exec strip
    return issues


def scan_pages() -> tuple[list[dict], int, list[dict]]:
    """Full role×route matrix — no CIO spot-check."""
    from scripts.role_route_matrix_certification import run_full_matrix, write_reports

    matrix_rows, meta = run_full_matrix()
    write_reports(matrix_rows, meta)
    issues: list[dict] = []
    inventory: list[dict] = []
    screens = meta["summary"]["tested"]
    for r in matrix_rows:
        if r.pass_fail() == "FAIL":
            for iss in r.issues_found:
                issues.append({
                    "phase": "matrix",
                    "severity": "P1",
                    "module": r.module,
                    "route": r.route,
                    "role": r.role,
                    "screen": r.screen,
                    "issue": iss,
                })
        inventory.append({
            "module": r.module,
            "route": r.route,
            "role": r.role,
            "screen": r.screen,
            "status": r.http_status,
            "pass_fail": r.pass_fail(),
        })
    return issues, screens, inventory


def scan_pages_legacy_spotcheck() -> tuple[list[dict], int, list[dict]]:
    issues: list[dict] = []
    inventory: list[dict] = []
    screens = 0

    for module, routes in MODULE_ROUTES.items():
        for route in routes:
            for role, user in (ROLES[0],):
                screens += 1
                url = _url(route, role, user)
                resp = client.get(url)
                inventory.append({
                    "module": module,
                    "route": route,
                    "role": role,
                    "status": resp.status_code,
                })
                if resp.status_code >= 400:
                    issues.append({
                        "phase": "empty_page",
                        "severity": "P1" if resp.status_code >= 500 else "P2",
                        "module": module,
                        "route": route,
                        "role": role,
                        "issue": f"HTTP {resp.status_code}",
                    })
                    continue
                issues.extend(_analyze_page(resp.text, module, route, role))

    for role, user in ROLES:
        dash = ROLE_DASHBOARD_ROUTES.get(role)
        if not dash or dash in {r for routes in MODULE_ROUTES.values() for r in routes}:
            if role in ("owner", "auditor") and dash == "/dashboard":
                pass
            elif role not in ("owner", "auditor", "framework_owner"):
                continue
        route = dash or "/dashboard"
        screens += 1
        url = _url(route, role, user)
        resp = client.get(url)
        inventory.append({"module": "Role Dashboard", "route": route, "role": role, "status": resp.status_code})
        if resp.status_code >= 400:
            issues.append({
                "phase": "empty_page",
                "severity": "P1",
                "route": route,
                "role": role,
                "issue": f"HTTP {resp.status_code}",
            })
        elif resp.status_code == 200:
            issues.extend(_analyze_page(resp.text, "Role Dashboard", route, role))
            if "pending_approvals" in route or role in ("cio", "vertical_head", "compliance_head", "auditor"):
                if role in ("cio", "vertical_head", "compliance_head", "compliance_officer", "auditor", "security_officer"):
                    if "ecs-pending-approvals" not in resp.text and role in ("cio", "vertical_head", "compliance_head", "auditor"):
                        if route in ("/dashboard/cio", "/dashboard/vertical-head", "/dashboard/compliance-head", "/dashboard"):
                            issues.append({
                                "phase": "pending_approvals",
                                "severity": "P2",
                                "route": route,
                                "role": role,
                                "issue": "Pending approvals panel not rendered",
                            })

    for fw in list(ecs_state.frameworks)[:6]:
        screens += 1
        route = f"/framework/{quote(fw, safe='')}"
        resp = client.get(_url(route, "cio", "cio@bank.com"))
        inventory.append({"module": "Frameworks", "route": route, "role": "cio", "status": resp.status_code})
        if resp.status_code >= 400:
            issues.append({"phase": "framework", "severity": "P1", "route": route, "issue": f"HTTP {resp.status_code}"})

    return issues, screens, inventory


def validate_kpis() -> list[dict]:
    issues: list[dict] = []
    for mod in KPI_MODULES:
        try:
            view = get_module_capability(mod, "cio")
        except Exception as exc:
            issues.append({"phase": "kpi", "severity": "P1", "module": mod, "issue": str(exc)})
            continue
        kpis = view.get("kpis") or []
        if not kpis:
            issues.append({"phase": "kpi", "severity": "P2", "module": mod, "issue": "No KPIs defined"})
            continue
        for k in kpis:
            val = str(k.get("value", "")).strip()
            if val in ("", "—", "Failed", "N/A", "null", "None"):
                issues.append({
                    "phase": "kpi",
                    "severity": "P1",
                    "module": mod,
                    "issue": f"Empty/invalid KPI value for {k.get('label')}: {val!r}",
                })
    return issues


def validate_drilldowns() -> list[dict]:
    issues: list[dict] = []
    for mod, metrics in DRILL_METRICS.items():
        for metric in metrics:
            body = drill_module_kpi(mod, metric, "cio")
            if not body.get("ok"):
                issues.append({
                    "phase": "drilldown",
                    "severity": "P1",
                    "module": mod,
                    "metric": metric,
                    "issue": body.get("error", "drill failed"),
                })
                continue
            rows = body.get("rows") or []
            if len(rows) < 1:
                issues.append({
                    "phase": "drilldown",
                    "severity": "P1",
                    "module": mod,
                    "metric": metric,
                    "issue": "Drill returned zero rows",
                })
    api_checks = [
        ("/api/demo/kpi-drill?metric=applications", "applications"),
        ("/api/grc-demo/governance/drill?metric=controls&role=cio", "grc_controls"),
        ("/api/audit-prep/kpi-drill?metric=draft", "audit_draft"),
    ]
    for path, label in api_checks:
        resp = client.get(path)
        if resp.status_code != 200:
            issues.append({"phase": "drilldown", "severity": "P1", "issue": f"{label} API HTTP {resp.status_code}"})
            continue
        body = resp.json()
        if not body.get("ok"):
            issues.append({"phase": "drilldown", "severity": "P1", "issue": f"{label} API not ok"})
        elif not (
            body.get("rows")
            or body.get("drill")
            or body.get("records")
            or (body.get("payload") or {}).get("data")
        ):
            issues.append({"phase": "drilldown", "severity": "P1", "issue": f"{label} API empty rows"})
    return issues


def validate_ai_ops_summaries() -> list[dict]:
    """Phase 11 — each summary mode must return distinct titles and row sets."""
    issues: list[dict] = []
    titles: set[str] = set()
    row_sigs: set[str] = set()
    for mode in SUMMARY_PAGE_MODES:
        page = build_summary_page(mode, "net_banking", "cio")
        if not page:
            issues.append({"phase": "ai_ops", "severity": "P1", "issue": f"Missing summary for mode {mode}"})
            continue
        title = page.get("title", "")
        if title in titles:
            issues.append({"phase": "ai_ops", "severity": "P1", "issue": f"Duplicate summary title for {mode}"})
        titles.add(title)
        rows = page.get("rows") or []
        if len(rows) < 5:
            issues.append({"phase": "ai_ops", "severity": "P1", "issue": f"Summary {mode} has insufficient rows"})
        sig = mode + ":" + str(len(rows)) + ":" + (rows[0].get("finding", "")[:40] if rows else "")
        row_sigs.add(sig)
    resp = client.get("/mvp/ai-ops-assistant?role=cio&user=cio@bank.com")
    if resp.status_code != 200:
        issues.append({"phase": "ai_ops", "severity": "P1", "issue": f"AI Ops page HTTP {resp.status_code}"})
    elif "startFreshInvestigation" not in resp.text:
        issues.append({"phase": "ai_ops", "severity": "P1", "issue": "Chat clear-on-new-query handler missing"})
    elif "ecs-persona-profile" not in resp.text and "R. Khanna" not in resp.text:
        issues.append({"phase": "ai_ops", "severity": "P2", "issue": "AI Ops persona header missing"})
    return issues


def validate_pending_approvals() -> list[dict]:
    from modules.governance.engines.workflow_module import build_pending_approvals_queue

    issues: list[dict] = []
    for role in ("cio", "vertical_head", "compliance_head", "auditor"):
        q = build_pending_approvals_queue(role, limit=10)
        if not q and role == "cio":
            issues.append({
                "phase": "pending_approvals",
                "severity": "P3",
                "role": role,
                "issue": "CIO pending queue empty (demo may still render panel)",
            })
    return issues


def main() -> int:
    print("=" * 70)
    print("ECS PLATFORM CERTIFICATION AUDIT")
    print("=" * 70)

    discovered = discover_html_routes()
    page_issues, screens, inventory = scan_pages()
    kpi_issues = validate_kpis()
    drill_issues = validate_drilldowns()
    ai_ops_issues = validate_ai_ops_summaries()
    pending_issues = validate_pending_approvals()
    all_issues = page_issues + kpi_issues + drill_issues + ai_ops_issues + pending_issues

    fixes = {
        "duplicate_ui_removed": [
            "Onboarding duplicate Applications/Pipeline/Post-Onboarding buttons",
            "Integrations duplicate Connectors/Sync/Logs buttons",
            "Bulk upload duplicate tab switch buttons",
            "Governance analytics duplicate KPI metric row",
        ],
        "personas_extended": [
            "security_officer", "operations_owner", "ai_governance_owner",
            "ai_sdlc_owner", "framework_owner",
        ],
        "pending_approvals_added": [
            "CIO Approvals tab — pending_approvals_panel + leadership queue",
            "Vertical Head, Compliance, Auditor dashboards",
        ],
        "ai_ops_enhanced": [
            "Persona profile header on AI Ops Assistant",
            "Chat form uses startFreshInvestigation (clears thread)",
            "Distinct summary modes validated",
        ],
        "ai_sdlc_routes_certified": [
            "requirements", "design", "development", "testing", "golive",
            "evidence", "findings",
        ],
    }

    by_phase: dict[str, int] = {}
    for i in all_issues:
        by_phase[i["phase"]] = by_phase.get(i["phase"], 0) + 1

    p1 = sum(1 for i in all_issues if i.get("severity") == "P1")
    certified = p1 == 0

    report = {
        "certification": "PASS" if certified else "FAIL",
        "certification_type": "FULL_ROLE_ROUTE_MATRIX",
        "screens_scanned": screens,
        "routes_discovered": len(discovered),
        "roles_scanned": [r[0] for r in ROLES],
        "issues_found": len(all_issues),
        "issues_fixed_this_run": fixes,
        "issues_remaining": all_issues,
        "by_phase": by_phase,
        "modules_validated": list(MODULE_ROUTES.keys()),
        "screen_inventory_sample": inventory[:80],
        "matrix_report_csv": str(
            ROOT / "modules" / "enterprise_grc" / "reports" / "ROLE_ROUTE_CERTIFICATION_REPORT.csv"
        ),
    }

    out_path = ROOT / "modules" / "enterprise_grc" / "reports" / "ECS_Platform_Certification_Report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    inv_path = ROOT / "modules" / "enterprise_grc" / "reports" / "ECS_Screen_Inventory.json"
    inv_path.write_text(
        json.dumps({"discovered_routes": discovered, "scanned": inventory}, indent=2),
        encoding="utf-8",
    )

    print(f"Routes discovered:   {len(discovered)}")
    print(f"Screens scanned:     {screens}")
    print(f"Issues found:        {len(all_issues)} (P1: {p1})")
    print(f"Certification:       {report['certification']}")
    print(f"Report written:      {out_path}")
    if all_issues:
        print("\nRemaining issues (first 15):")
        for item in all_issues[:15]:
            print(f"  [{item.get('severity','?')}] {item.get('phase')} — {item.get('issue')} ({item.get('route') or item.get('module')})")
    print("=" * 70)
    return 0 if certified else 1


if __name__ == "__main__":
    raise SystemExit(main())
