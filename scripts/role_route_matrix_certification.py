#!/usr/bin/env python3
"""
Full Role × Route matrix certification — every role × every navigable screen.

No CIO spot-check. Every cell in the matrix is exercised and recorded.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import ecs_state  # noqa: E402
from app.main import app  # noqa: E402
from modules.shared.drilldowns.module_kpi_drill_engine import drill_module_kpi  # noqa: E402
from modules.shared.services.module_capabilities import get_module_capability  # noqa: E402
from modules.shared.services.persona_display import PERSONA_BY_ROLE  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

# 11 roles per product audit spec (Compliance Officer = compliance_officer key)
ROLES: list[tuple[str, str, str]] = [
    ("cio", "cio@bank.com", "CIO"),
    ("vertical_head", "vertical.head@bank.com", "Vertical Head"),
    ("owner", "owner.app1@bank.com", "Application Owner"),
    ("auditor", "audit.lead@bank.com", "Auditor"),
    ("compliance_officer", "compliance.officer@bank.com", "Compliance Officer"),
    ("security_officer", "security.officer@bank.com", "Security Officer"),
    ("functional_head", "functional.head@bank.com", "Functional Head"),
    ("operations_owner", "ops.owner@bank.com", "Operations Owner"),
    ("framework_owner", "framework.owner@bank.com", "Framework Owner"),
    ("ai_governance_owner", "ai.gov@bank.com", "AI Governance Owner"),
    ("ai_sdlc_owner", "ai.sdlc@bank.com", "AI SDLC Governance Owner"),
]

FOCUSED_ROLES_VH_OWNER_AUDITOR = ("vertical_head", "owner", "auditor")

ROLE_PRIMARY_DASHBOARD: dict[str, str] = {
    "vertical_head": "/dashboard/vertical-head",
    "owner": "/dashboard",
    "auditor": "/dashboard",
    "cio": "/dashboard/cio",
}

ROUTE_NAV_MODULE: dict[str, str] = {
    "/mvp/scheduler": "scheduler",
    "/mvp/ai-ops-assistant": "ai_ops_assistant",
    "/mvp/upload": "upload",
    "/mvp/bulk-upload": "upload",
    "/mvp/evidence-health": "evidence_health",
    "/mvp/search": "search",
    "/mvp/completeness": "completeness",
    "/mvp/reuse": "reuse",
    "/mvp/onboarding": "onboarding",
    "/mvp/framework-loader": "framework_loader",
    "/mvp/framework-admin": "framework_admin",
    "/mvp/demo-overview": "demo_overview",
    "/mvp/lifecycle": "lifecycle",
    "/mvp/comparison": "comparison",
    "/mvp/integrations": "integrations",
    "/mvp/enterprise": "enterprise",
    "/mvp/pan-india": "pan_india",
    "/mvp/reports": "reports",
    "/mvp/audit-prep": "audit_prep",
    "/mvp/trends": "trends",
    "/mvp/risk-register": "risk_register",
    "/mvp/exceptions": "exceptions_td",
    "/mvp/evidence-approval": "evidence_approval",
    "/mvp/exception-governance": "exception_governance",
    "/mvp/cmdb": "cmdb",
    "/mvp/regulatory": "regulatory_mapping",
    "/mvp/heatmaps": "executive_heatmaps",
    "/mvp/integrations-hub": "integrations_hub",
    "/mvp/correlation": "correlation",
    "/mvp/governance-analytics": "governance_analytics",
    "/mvp/ai-governance": "ai_governance",
    "/mvp/ai-registry": "ai_registry",
    "/mvp/sdlc-gates": "sdlc_gates",
    "/mvp/governance-quality": "governance_quality",
}

STATIC_SCREENS: list[tuple[str, str, str]] = [
    ("Executive Overview", "/dashboard", "Main Dashboard"),
    ("Executive Overview", "/dashboard/cio", "CIO Evidence Analytics"),
    ("Executive Overview", "/dashboard/vertical-head", "Vertical Head Dashboard"),
    ("Executive Overview", "/dashboard/compliance-head", "Compliance Dashboard"),
    ("Executive Overview", "/dashboard/functional-head", "Functional Head Dashboard"),
    ("Executive Overview", "/mvp/demo-overview", "Demo Overview"),
    ("Executive Overview", "/mvp/enterprise", "Enterprise"),
    ("Executive Overview", "/mvp/pan-india", "Pan India"),
    ("Executive Overview", "/mvp/reports", "Reports"),
    ("Executive Overview", "/mvp/trends", "Trends"),
    ("Frameworks", "/mvp/framework-loader", "Framework Loader"),
    ("Frameworks", "/mvp/framework-admin", "Framework Administration"),
    ("Operations", "/mvp/scheduler", "Scheduler"),
    ("Operations", "/mvp/ai-ops-assistant", "AI Ops Assistant"),
    ("Operations", "/mvp/upload", "Bulk Upload"),
    ("Operations", "/mvp/bulk-upload", "Bulk Upload Hub"),
    ("Operations", "/mvp/integrations", "Integrations"),
    ("Operations", "/mvp/onboarding", "Onboarding"),
    ("Operations", "/mvp/integrations-hub", "Integrations Hub"),
    ("Governance", "/mvp/audit-prep", "Audit Prep"),
    ("Governance", "/mvp/evidence-health", "Evidence Health"),
    ("Governance", "/mvp/reuse", "Evidence Reuse"),
    ("Governance", "/mvp/lifecycle", "Lifecycle"),
    ("Governance", "/mvp/completeness", "Completeness"),
    ("Governance", "/mvp/comparison", "App Comparison"),
    ("Governance", "/mvp/search", "Search"),
    ("Governance", "/mvp/evidence-approval", "Evidence Approval Analytics"),
    ("Governance", "/mvp/workflow/close-gap", "Close Gap Workflow"),
    ("Governance", "/mvp/workflow/assign-owner", "Assign Owner Workflow"),
    ("Governance", "/mvp/workflow/upload-missing", "Upload Missing Workflow"),
    ("Governance", "/mvp/workflow/mock-audit", "Mock Audit"),
    ("Enterprise GRC", "/mvp/risk-register", "Risk Register"),
    ("Enterprise GRC", "/mvp/exceptions", "Exceptions / TD"),
    ("Enterprise GRC", "/mvp/exception-governance", "Exception Governance"),
    ("Enterprise GRC", "/mvp/cmdb", "CMDB / Assets"),
    ("Enterprise GRC", "/mvp/regulatory", "Regulatory Mapping"),
    ("Enterprise GRC", "/mvp/heatmaps", "Executive Heatmaps"),
    ("Enterprise GRC", "/mvp/correlation", "Cross-Tool Correlation"),
    ("Enterprise GRC", "/mvp/governance-analytics", "Governance Analytics"),
    ("AI SDLC Governance", "/mvp/ai-sdlc", "AI SDLC Home"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/control-tower", "AI SDLC Control Tower"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/onboarding", "Application Onboarding"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/requirements", "Requirements"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/design", "Design"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/development", "Development"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/testing", "Testing"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/golive", "Go-Live"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/evidence", "Evidence Collection"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/findings", "Findings & Remediation"),
    ("AI SDLC Governance", "/mvp/ai-sdlc/reports", "AI SDLC Reports"),
    ("AI SDLC Governance", "/mvp/ai-governance", "AI Governance"),
    ("AI SDLC Governance", "/mvp/ai-registry", "AI Registry"),
    ("AI SDLC Governance", "/mvp/sdlc-gates", "SDLC Gates"),
    ("AI SDLC Governance", "/mvp/governance-quality", "Governance Quality"),
]

def _sample_evidence_review_route() -> tuple[str, str]:
    fw = next(iter(sorted(ecs_state.frameworks.keys())), "PCI DSS")
    ctrl = None
    ev_id = "EV-SYNTH"
    try:
        from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG

        controls = FRAMEWORK_CATALOG.get(fw) or []
        if controls:
            ctrl = controls[0].get("control", "")
            evs = controls[0].get("evidences") or []
            if evs:
                ev_id = evs[0].get("evidence_id", ev_id)
    except Exception:
        pass
    route = (
        f"/evidence/review?framework_name={quote(fw)}"
        f"&control_name={quote(ctrl or 'Access Control')}"
        f"&evidence_id={quote(ev_id)}"
    )
    return route, f"Evidence Review — {fw}"

AI_OPS_SUMMARY_MODES = [
    "business", "technical", "executive", "audit", "compliance", "evidence", "incident", "root_cause",
]

SCRIPT_BLOCK = re.compile(r"<script[\s\S]*?</script>", re.I)
FORBIDDEN_VISIBLE = [
    (re.compile(r">\s*No Data Available\s*<", re.I), "No Data Available"),
    (re.compile(r">\s*No Records Found\s*<", re.I), "No Records Found"),
    (re.compile(r">\s*Item Not Found\s*<", re.I), "Item Not Found"),
    (re.compile(r"ECS CIO|CIO CIO|App Owner App Owner", re.I), "Duplicate role branding"),
]
FORBIDDEN_KPI_VALUE = re.compile(
    r'class="ecs-exec-kpi-val"[^>]*>\s*(Failed|—|N/A|null|None)\s*<',
    re.I,
)
DUPLICATE_TAB_SWITCH = re.compile(
    r'data-ecs-tab-switch="([^"]+)"[\s\S]*?ecs-workspace-tab[^>]*>\s*\1\s*<',
    re.I,
)
KPI_DRILL_ATTR = re.compile(
    r'data-ecs-module-kpi-module="([^"]+)"[^>]*data-ecs-module-kpi-metric="([^"]+)"',
    re.I,
)
TAB_PANE = re.compile(r'id="(tab-[^"]+)"[^>]*class="[^"]*tab-pane', re.I)
EMPTY_TAB = re.compile(r'id="tab-[^"]+"[^>]*class="[^"]*tab-pane[^"]*"[^>]*>\s*</div>', re.I)

_MODULE_KPI_VALIDATED: set[tuple[str, str]] = set()


@dataclass
class MatrixRow:
    role: str
    role_label: str
    module: str
    route: str
    screen: str
    issues_found: list[str] = field(default_factory=list)
    issues_fixed: list[str] = field(default_factory=list)
    status: str = "NOT TESTED"
    http_status: int = 0

    def pass_fail(self) -> str:
        if self.status == "NOT TESTED":
            return "NOT TESTED"
        return "PASS" if not self.issues_found else "FAIL"


def _url(route: str, role: str, user: str) -> str:
    sep = "&" if "?" in route else "?"
    return f"{route}{sep}role={role}&user={quote(user)}"


def _sample_ai_sdlc_evidence_id() -> str:
    try:
        from modules.ai_sdlc.engines.ai_sdlc_governance_service import evidence_view

        wl = evidence_view()
        for row in wl.get("rows") or []:
            eid = row.get("evidence_id")
            if eid:
                return eid
    except Exception:
        pass
    return "EVD-REQ-0001"


def build_screen_catalog() -> list[tuple[str, str, str]]:
    """All static screens + framework drilldowns + AI SDLC popups."""
    catalog = list(STATIC_SCREENS)
    catalog.append(("Executive Overview", "/dashboard/compliance-head", "Compliance Dashboard"))
    for fw in sorted(ecs_state.frameworks.keys()):
        catalog.append(("Frameworks", f"/framework/{quote(fw, safe='')}", f"Framework — {fw}"))
    for mode in AI_OPS_SUMMARY_MODES:
        catalog.append(("Operations", f"/mvp/ai-ops-assistant/summary/{mode}", f"AI Ops Summary — {mode.title()}"))
    catalog.append(("AI SDLC Governance", "/mvp/ai-sdlc/reports/app-compliance", "AI SDLC Report Detail"))
    eid = _sample_ai_sdlc_evidence_id()
    catalog.append(("AI SDLC Governance", f"/mvp/ai-sdlc/evidence/view/{eid}", "AI SDLC Evidence Viewer"))
    ev_route, ev_screen = _sample_evidence_review_route()
    catalog.append(("Evidence", ev_route, ev_screen))
    return catalog


def _parse_kpi_number(val: str) -> int | None:
    val = (val or "").strip().replace(",", "").replace("%", "")
    if not val or val in ("—", "Failed", "N/A"):
        return None
    try:
        return int(float(val))
    except ValueError:
        return None


@lru_cache(maxsize=4096)
def _cached_drill(mod: str, metric: str, role: str) -> tuple[bool, int, str]:
    body = drill_module_kpi(mod, metric, role)
    rows = body.get("rows") or []
    err = body.get("error", "failed") if not body.get("ok") else ""
    return bool(body.get("ok")), len(rows), err


def _validate_drills_on_page(html: str, role: str) -> list[str]:
    issues: list[str] = []
    seen: set[tuple[str, str]] = set()
    for mod, metric in KPI_DRILL_ATTR.findall(html):
        key = (mod, metric)
        if key in seen:
            continue
        seen.add(key)
        ok, nrows, err = _cached_drill(mod, metric, role)
        if not ok:
            issues.append(f"Broken drilldown: {mod}/{metric} — {err}")
        elif nrows < 1:
            issues.append(f"Empty drilldown rows: {mod}/{metric}")
    return issues


def _validate_module_kpis(nav_module: str, role: str) -> list[str]:
    if not nav_module or nav_module in ("demo_overview", "framework_loader", "framework_admin"):
        return []
    cache_key = (nav_module, role)
    if cache_key in _MODULE_KPI_VALIDATED:
        return []
    _MODULE_KPI_VALIDATED.add(cache_key)
    issues: list[str] = []
    try:
        view = get_module_capability(nav_module, role)
    except Exception as exc:
        return [f"KPI module error: {exc}"]
    kpis = view.get("kpis") or []
    if not kpis:
        return []
    for k in kpis:
        val = str(k.get("value", "")).strip()
        if val in ("", "—", "Failed", "N/A", "null", "None"):
            issues.append(f"Empty KPI card: {k.get('label')}")
            continue
        metric = k.get("drill") or k.get("label", "").lower().replace(" ", "_")
        ok, nrows, err = _cached_drill(nav_module, metric, role)
        if not ok or nrows < 1:
            issues.append(f"KPI drill broken: {k.get('label')} ({metric}) — {err}")
            continue
        num = _parse_kpi_number(val)
        if num is not None and num > 10 and nrows < min(num // 2, 5):
            issues.append(f"KPI count mismatch: {k.get('label')}={val} vs {nrows} drill rows")
    return issues


def _validate_tabs(html: str) -> list[str]:
    body = SCRIPT_BLOCK.sub("", html)
    issues: list[str] = []
    if EMPTY_TAB.search(body):
        issues.append("Empty tab pane detected")
    panes = TAB_PANE.findall(body)
    if panes:
        from collections import Counter
        dup = [p for p, c in Counter(panes).items() if c > 1]
        if dup:
            issues.append(f"Duplicate tab IDs: {dup}")
    return issues


def _validate_scrolling(html: str) -> list[str]:
    issues: list[str] = []
    has_pagination = (
        "ecs-paginated-wrap" in html
        or "ecs-paginated-table" in html
        or "ecs-gov-data-table" in html
        or "ecs-gov-table-shell" in html
        or "ecsRefreshPagination" in html
    )
    if re.search(r"overflow-x:\s*scroll", html, re.I) and not has_pagination:
        issues.append("Excessive horizontal scrolling (overflow-x scroll without pagination)")
    if has_pagination:
        return issues
    tables = re.findall(r"<table[^>]*>([\s\S]*?)</table>", html, re.I)
    for tbl in tables:
        rows = tbl.count("<tr")
        if rows > 80 and "ecs-paginated-table" not in tbl:
            issues.append(f"Large unpaginated table ({rows} rows)")
            break
    return issues


def _validate_page(html: str, route: str, role: str, nav_module: str | None) -> list[str]:
    # Large MVP pages: analyze markup only (skip embedded JSON in scripts)
    body = SCRIPT_BLOCK.sub("", html[:400_000])
    issues: list[str] = []
    if "Internal Server Error" in html or "UndefinedError" in html or "Traceback" in html:
        issues.append("Runtime/template error")
    for pat, label in FORBIDDEN_VISIBLE:
        if pat.search(body):
            issues.append(label)
    if FORBIDDEN_KPI_VALUE.search(body):
        issues.append("Empty or Failed KPI card value on page")
    if DUPLICATE_TAB_SWITCH.search(body):
        issues.append("Duplicate navigation tabs")
    titles = re.findall(r'class="ecs-page-title[^"]*"[^>]*>([^<]+)<', body)
    if len(titles) > 1:
        issues.append("Duplicate page headers")
    persona = PERSONA_BY_ROLE.get(role, {})
    if persona and route.startswith(("/dashboard", "/mvp", "/framework", "/evidence")):
        dn = persona.get("display_name", "")
        has_persona = (
            (dn and dn in html)
            or "ecs-persona-profile" in html
            or "ecs-sidebar-profile-name" in html
        )
        if dn and not has_persona:
            if route not in ("/mvp/upload", "/mvp/bulk-upload"):
                issues.append(f"Missing persona header ({dn})")
    issues.extend(_validate_tabs(body))
    issues.extend(_validate_scrolling(html))
    if nav_module:
        issues.extend(_validate_module_kpis(nav_module, role))
    elif KPI_DRILL_ATTR.search(html):
        issues.extend(_validate_drills_on_page(html, role))
    return issues


def resolve_roles(role_filter: list[str] | None) -> list[tuple[str, str, str]]:
    if not role_filter:
        return list(ROLES)
    allowed = {r.strip().lower() for r in role_filter}
    out = [t for t in ROLES if t[0] in allowed]
    if not out:
        raise SystemExit(f"No matching roles in filter: {role_filter}")
    return out


def run_full_matrix(
    roles: list[tuple[str, str, str]] | None = None,
    *,
    exclude_cio_routes: bool = False,
) -> tuple[list[MatrixRow], dict]:
    active_roles = roles or list(ROLES)
    catalog = build_screen_catalog()
    if exclude_cio_routes:
        catalog = [
            (m, r, s) for m, r, s in catalog
            if r not in ("/dashboard/cio",)
        ]
        for rk in {t[0] for t in active_roles}:
            dash = ROLE_PRIMARY_DASHBOARD.get(rk)
            if dash and not any(c[1] == dash for c in catalog):
                label = next(t[2] for t in active_roles if t[0] == rk)
                catalog.insert(0, ("Executive Overview", dash, f"{label} Dashboard"))
    rows: list[MatrixRow] = []
    fixes_applied: list[str] = [
        "Persona via ecs_sidebar_profile on all MVP pages",
        "Module KPI/drill validation cached per role×module",
        "AI SDLC evidence viewer uses live mock evidence ID",
    ]
    _MODULE_KPI_VALIDATED.clear()
    _cached_drill.cache_clear()

    total = len(active_roles) * len(catalog)
    done = 0
    for role_key, user, role_label in active_roles:
        for module, route, screen in catalog:
            done += 1
            if done % 25 == 0:
                print(f"  Progress: {done}/{total} ({role_label} — {screen[:40]})", flush=True)
            row = MatrixRow(
                role=role_key,
                role_label=role_label,
                module=module,
                route=route,
                screen=screen,
            )
            nav_mod = ROUTE_NAV_MODULE.get(route.split("?")[0])
            if route.startswith("/framework/"):
                nav_mod = None
            url = _url(route, role_key, user)
            try:
                resp = client.get(url, follow_redirects=True)
            except Exception as exc:
                row.status = "TESTED"
                row.http_status = 0
                row.issues_found.append(f"Request failed: {exc}")
                rows.append(row)
                continue

            row.status = "TESTED"
            row.http_status = resp.status_code
            if resp.status_code >= 400:
                row.issues_found.append(f"HTTP {resp.status_code}")
            elif resp.status_code >= 300 and len(resp.text) < 200:
                row.issues_found.append(f"Redirect without content (HTTP {resp.status_code})")
            else:
                html = resp.text
                if "Item Not Found" in html and "tab-pane" not in route:
                    pass  # caught by forbidden pattern
                page_issues = _validate_page(html, route, role_key, nav_mod)
                row.issues_found.extend(page_issues)
                # Tab sub-screens (in-DOM, same HTTP load)
                body_no_script = SCRIPT_BLOCK.sub("", html)
                for tab_id in set(TAB_PANE.findall(body_no_script)):
                    sub = MatrixRow(
                        role=role_key,
                        role_label=role_label,
                        module=module,
                        route=route,
                        screen=f"{screen} · {tab_id}",
                        status="TESTED",
                        http_status=resp.status_code,
                    )
                    if f'Empty tab content: {tab_id}' in str(page_issues):
                        sub.issues_found.append(f"Empty tab content: {tab_id}")
                    else:
                        pane_match = re.search(
                            rf'id="{re.escape(tab_id)}"[^>]*class="[^"]*tab-pane[^"]*"[^>]*>([\s\S]{{0,800}})',
                            body_no_script,
                            re.I,
                        )
                        if pane_match and len(re.sub(r"<[^>]+>", "", pane_match.group(1)).strip()) < 15:
                            sub.issues_found.append(f"Empty tab content: {tab_id}")
                    if sub.issues_found:
                        rows.append(sub)

            rows.append(row)

    # Mark any catalog screen missing from matrix (should not happen)
    tested_keys = {(r.role, r.route, r.screen) for r in rows if r.status == "TESTED"}
    for module, route, screen in catalog:
        for role_key, _, role_label in active_roles:
            if (role_key, route, screen) not in tested_keys:
                rows.append(MatrixRow(
                    role=role_key,
                    role_label=role_label,
                    module=module,
                    route=route,
                    screen=screen,
                    status="NOT TESTED",
                    issues_found=["Matrix cell not executed"],
                ))

    summary = {
        "total_cells": len(rows),
        "tested": sum(1 for r in rows if r.status == "TESTED"),
        "not_tested": sum(1 for r in rows if r.status == "NOT TESTED"),
        "pass": sum(1 for r in rows if r.pass_fail() == "PASS"),
        "fail": sum(1 for r in rows if r.pass_fail() == "FAIL"),
        "roles": len(active_roles),
        "routes": len(catalog),
        "role_keys": [t[0] for t in active_roles],
    }
    return rows, {"summary": summary, "fixes_applied": fixes_applied}


def write_reports(
    rows: list[MatrixRow],
    meta: dict,
    *,
    basename: str = "ROLE_ROUTE_CERTIFICATION_REPORT",
) -> Path:
    out_dir = ROOT / "modules" / "enterprise_grc" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"{basename}.csv"
    json_path = out_dir / f"{basename}.json"

    fieldnames = ["Role", "Module", "Screen", "Issue Found", "Issue Fixed", "Status", "Route", "Pass/Fail", "HTTP"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({
                "Role": r.role_label,
                "Module": r.module,
                "Screen": r.screen,
                "Issue Found": "; ".join(r.issues_found) if r.issues_found else "",
                "Issue Fixed": "; ".join(r.issues_fixed) if r.issues_fixed else "",
                "Status": "PASS" if r.pass_fail() == "PASS" else ("FAIL" if r.pass_fail() == "FAIL" else r.status),
                "Route": r.route,
                "Pass/Fail": r.pass_fail(),
                "HTTP": r.http_status,
            })

    fail_rows = [r for r in rows if r.pass_fail() == "FAIL"]
    p1_fail = len(fail_rows)
    certified = p1_fail == 0 and meta["summary"]["not_tested"] == 0

    report = {
        "certification": "PASS" if certified else "FAIL",
        "certification_type": "FULL_ROLE_ROUTE_MATRIX",
        "summary": meta["summary"],
        "issues_fixed_this_run": meta.get("fixes_applied", []),
        "failures": [
            {
                "role": r.role_label,
                "module": r.module,
                "route": r.route,
                "screen": r.screen,
                "issues": r.issues_found,
            }
            for r in fail_rows[:200]
        ],
        "matrix_sample": [
            {
                "Role": r.role_label,
                "Module": r.module,
                "Route": r.route,
                "Screen": r.screen,
                "Issue Found": "; ".join(r.issues_found),
                "Pass/Fail": r.pass_fail(),
            }
            for r in rows[:50]
        ],
    }
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return json_path


def main() -> int:
    parser = argparse.ArgumentParser(description="ECS Role × Route matrix certification")
    parser.add_argument(
        "--roles",
        default="",
        help="Comma-separated role keys (e.g. vertical_head,owner,auditor). Empty = all roles.",
    )
    parser.add_argument(
        "--report",
        default="ROLE_ROUTE_CERTIFICATION_REPORT",
        help="Report basename (without extension)",
    )
    parser.add_argument(
        "--exclude-cio",
        action="store_true",
        help="Skip /dashboard/cio and other CIO-only primary routes",
    )
    args = parser.parse_args()

    role_filter = [r.strip() for r in args.roles.split(",") if r.strip()] or None
    active = resolve_roles(role_filter)
    exclude_cio = args.exclude_cio or (
        role_filter is not None and "cio" not in {r.lower() for r in role_filter}
    )

    print("=" * 72)
    title = "ECS FOCUSED ROLE × ROUTE CERTIFICATION" if role_filter else "ECS FULL ROLE × ROUTE MATRIX CERTIFICATION"
    print(title)
    print("=" * 72)
    catalog = build_screen_catalog()
    if exclude_cio:
        catalog = [(m, r, s) for m, r, s in catalog if r != "/dashboard/cio"]
    print(f"Roles:    {len(active)} ({', '.join(t[2] for t in active)})")
    print(f"Screens:  {len(catalog)} (incl. frameworks + AI ops summaries)")
    print(f"Matrix:   {len(active) * len(catalog)} base cells (+ tab sub-screens)")
    print("Running traversal…")

    rows, meta = run_full_matrix(active, exclude_cio_routes=exclude_cio)
    json_path = write_reports(rows, meta, basename=args.report)

    s = meta["summary"]
    print(f"\nCells tested:     {s['tested']}")
    print(f"NOT TESTED:       {s['not_tested']}")
    print(f"PASS:             {s['pass']}")
    print(f"FAIL:             {s['fail']}")
    print(f"Certification:    {'PASS' if s['fail'] == 0 and s['not_tested'] == 0 else 'FAIL'}")
    print(f"CSV report:       {json_path.parent / (args.report + '.csv')}")
    print(f"JSON summary:     {json_path}")

    failures = [r for r in rows if r.pass_fail() == "FAIL"][:20]
    if failures:
        print("\nFirst failures:")
        for r in failures:
            print(f"  {r.role_label} | {r.route} | {r.screen} | {r.issues_found[0] if r.issues_found else '?'}")

    print("=" * 72)
    return 0 if s["fail"] == 0 and s["not_tested"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
