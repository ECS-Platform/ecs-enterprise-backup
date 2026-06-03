#!/usr/bin/env python3
"""Module-focused certification for CIO and App Owner — no full route matrix."""

from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import ecs_state  # noqa: E402
from app.main import app  # noqa: E402
from modules.shared.drilldowns.module_kpi_drill_engine import drill_module_kpi  # noqa: E402
from modules.shared.services.module_capabilities import get_module_capability  # noqa: E402
from modules.operations.engines.ai_ops_summary_engine import SUMMARY_PAGE_MODES, build_summary_page  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

ROLES = [
    ("cio", "cio@bank.com", "CIO"),
    ("owner", "owner.app1@bank.com", "Application Owner"),
]

# Module → representative routes and capability keys to validate
MODULE_SPEC: dict[str, dict] = {
    "Executive Overview": {
        "routes": ["/mvp/demo-overview", "/mvp/enterprise", "/mvp/pan-india"],
        "nav_modules": ["demo_overview", "enterprise", "pan_india"],
        "require_charts": True,
    },
    "Evidence Analytics": {
        "routes_by_role": {"cio": ["/dashboard/cio"], "owner": ["/dashboard"]},
        "nav_modules": [],
        "require_kpi_macro": True,
        "require_charts": True,
    },
    "Trends": {
        "routes": ["/mvp/trends"],
        "nav_modules": ["trends"],
        "require_charts": True,
    },
    "Reports": {
        "routes": ["/mvp/reports"],
        "nav_modules": ["reports"],
        "require_charts": False,
    },
    "Frameworks": {
        "routes": ["/mvp/framework-loader"],
        "nav_modules": ["framework_loader"],
        "framework_sample": True,
        "require_evidence_links": True,
    },
    "Operations": {
        "routes": ["/mvp/scheduler", "/mvp/ai-ops-assistant", "/mvp/onboarding"],
        "nav_modules": ["scheduler", "ai_ops_assistant", "onboarding"],
        "require_copilot": True,
    },
    "Governance": {
        "routes": [
            "/mvp/audit-prep",
            "/mvp/evidence-health",
            "/mvp/search",
            "/mvp/completeness",
        ],
        "nav_modules": ["audit_prep", "evidence_health", "search", "completeness"],
        "require_evidence_links": False,
    },
    "AI SDLC Governance": {
        "routes": [
            "/mvp/ai-sdlc",
            "/mvp/ai-sdlc/control-tower",
            "/mvp/ai-sdlc/evidence",
            "/mvp/ai-sdlc/findings",
        ],
        "nav_modules": [],
        "require_evidence_links": True,
        "require_observation_links": True,
    },
}

FORBIDDEN = [
    (re.compile(r">\s*No Data Available\s*<", re.I), "No Data Available"),
    (re.compile(r">\s*No Records Found\s*<", re.I), "No Records Found"),
    (re.compile(r">\s*Item Not Found\s*<", re.I), "Item Not Found"),
]
KPI_DRILL_ATTR = re.compile(
    r'data-ecs-module-kpi-module="([^"]+)"[^>]*data-ecs-module-kpi-metric="([^"]+)"',
    re.I,
)


@dataclass
class Finding:
    role: str
    module: str
    check: str
    issue: str
    fixed: str = ""

    @property
    def status(self) -> str:
        return "PASS" if not self.issue else "FAIL"


@dataclass
class CertReport:
    findings: list[Finding] = field(default_factory=list)
    fixes_applied: list[str] = field(default_factory=list)

    def add(self, role: str, module: str, check: str, issue: str = "", fixed: str = ""):
        self.findings.append(Finding(role, module, check, issue, fixed))


def _url(route: str, role: str, user: str) -> str:
    sep = "&" if "?" in route else "?"
    return f"{route}{sep}role={role}&user={quote(user)}"


def _sample_framework_route() -> str:
    fw = next(iter(sorted(ecs_state.frameworks.keys())), "PCI DSS")
    return f"/framework/{quote(fw, safe='')}"


def _sample_evidence_review_route() -> str:
    fw = "PCI DSS" if "PCI DSS" in ecs_state.frameworks else next(iter(ecs_state.frameworks.keys()))
    from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG

    ctrl, ev_id = "Access Control", "EV-SYNTH"
    controls = FRAMEWORK_CATALOG.get(fw) or []
    if controls:
        ctrl = controls[0].get("control", ctrl)
        evs = controls[0].get("evidences") or []
        if evs:
            ev_id = evs[0].get("evidence_id", ev_id)
    return (
        f"/evidence/review?framework_name={quote(fw)}"
        f"&control_name={quote(ctrl)}&evidence_id={quote(ev_id)}"
    )


def _routes_for_module(module: str, role_key: str) -> list[str]:
    spec = MODULE_SPEC[module]
    if "routes_by_role" in spec:
        return list(spec["routes_by_role"].get(role_key, []))
    routes = list(spec.get("routes", []))
    if spec.get("framework_sample"):
        routes.append(_sample_framework_route())
    return routes


def validate_page_load(role: str, role_label: str, module: str, route: str, report: CertReport) -> str | None:
    user = next(u for r, u, _ in ROLES if r == role)
    resp = client.get(_url(route, role, user), follow_redirects=True)
    if resp.status_code >= 400:
        report.add(role_label, module, f"Page load {route}", f"HTTP {resp.status_code}")
        return None
    html = resp.text
    if "Internal Server Error" in html or "UndefinedError" in html:
        report.add(role_label, module, f"Page load {route}", "Runtime/template error")
        return None
    body = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)[:300_000]
    for pat, label in FORBIDDEN:
        if pat.search(body):
            report.add(role_label, module, f"Empty state {route}", label)
    return html


def validate_kpis(role: str, role_label: str, module: str, nav_module: str, report: CertReport):
    if not nav_module:
        return
    try:
        view = get_module_capability(nav_module, role)
    except Exception as exc:
        report.add(role_label, module, f"KPI capability {nav_module}", str(exc))
        return
    kpis = view.get("kpis") or []
    if not kpis:
        report.add(role_label, module, f"KPI cards {nav_module}", "No KPIs defined")
        return
    for k in kpis:
        val = str(k.get("value", "")).strip()
        if val in ("", "—", "Failed", "N/A", "null", "None"):
            report.add(role_label, module, f"KPI {k.get('label')}", f"Invalid value: {val!r}")
            continue
        metric = k.get("drill") or str(k.get("label", "")).lower().replace(" ", "_")
        body = drill_module_kpi(nav_module, metric, role)
        if not body.get("ok") or len(body.get("rows") or []) < 1:
            report.add(role_label, module, f"KPI drill {nav_module}/{metric}", body.get("error", "empty drill rows"))
        else:
            report.add(role_label, module, f"KPI drill {nav_module}/{metric}", "")


def validate_charts(role_label: str, module: str, html: str | None, report: CertReport):
    if not html:
        return
    spec = MODULE_SPEC[module]
    if not spec.get("require_charts"):
        return
    if "canvas" in html or "ecs-chart" in html or "executive_charts" in html or "Chart(" in html:
        report.add(role_label, module, "Charts", "")
    else:
        report.add(role_label, module, "Charts", "No chart markup detected on analytics page")


def validate_drilldowns_on_page(role: str, role_label: str, module: str, html: str | None, report: CertReport):
    if not html:
        return
    seen: set[tuple[str, str]] = set()
    for mod, metric in KPI_DRILL_ATTR.findall(html):
        key = (mod, metric)
        if key in seen:
            continue
        seen.add(key)
        body = drill_module_kpi(mod, metric, role)
        if not body.get("ok") or len(body.get("rows") or []) < 1:
            report.add(role_label, module, f"Page KPI drill {mod}/{metric}", "Drill failed or empty")
        else:
            report.add(role_label, module, f"Page KPI drill {mod}/{metric}", "")


def validate_popups(role_label: str, module: str, html: str | None, report: CertReport):
    if not html:
        return
    if (
        "modal" in html.lower()
        or "ecs-drill" in html
        or "drilldown_engine" in html
        or "ecs-governance-modal" in html
        or "data-bs-toggle=\"modal\"" in html
    ):
        report.add(role_label, module, "Popups/modals", "")
    else:
        report.add(role_label, module, "Popups/modals", "No modal/drilldown shell detected")


def validate_copilot(role: str, role_label: str, module: str, report: CertReport):
    if not MODULE_SPEC[module].get("require_copilot"):
        return
    user = next(u for r, u, _ in ROLES if r == role)
    fd = {"query": "Why is Net Banking latency elevated?", "role": role, "user": user}
    inv = client.post("/mvp/api/chat-investigation", data=fd)
    if inv.status_code != 200:
        report.add(role_label, module, "Copilot investigation", f"HTTP {inv.status_code}")
        return
    data = inv.json()
    if not data.get("ok") or not data.get("html"):
        report.add(role_label, module, "Copilot investigation", data.get("error", "empty response"))
    else:
        report.add(role_label, module, "Copilot investigation", "")
    fd2 = {"scenario_key": "net_banking", "mode": "executive", "role": role, "user": user}
    mode = client.post("/mvp/api/chat-response-mode", data=fd2)
    if mode.status_code != 200 or not (mode.json() or {}).get("ok"):
        report.add(role_label, module, "Copilot summary mode", "Response mode API failed")
    else:
        report.add(role_label, module, "Copilot summary mode", "")
    titles = set()
    for m in SUMMARY_PAGE_MODES:
        page = build_summary_page(m, "net_banking", role)
        if page:
            titles.add(page.get("title", ""))
    if len(titles) < len(SUMMARY_PAGE_MODES) - 1:
        report.add(role_label, module, "Copilot summary modes", "Distinct summary pages missing")
    else:
        report.add(role_label, module, "Copilot summary modes", "")


def validate_evidence_observation_links(
    role: str, role_label: str, module: str, html: str | None, report: CertReport
):
    spec = MODULE_SPEC[module]
    user = next(u for r, u, _ in ROLES if r == role)
    if spec.get("require_evidence_links"):
        ev_route = _sample_evidence_review_route()
        resp = client.get(_url(ev_route, role, user))
        if resp.status_code >= 400:
            report.add(role_label, module, "Evidence review link", f"HTTP {resp.status_code}")
        elif "Item Not Found" in resp.text or "No Data Available" in resp.text:
            report.add(role_label, module, "Evidence review link", "Empty evidence viewer")
        else:
            report.add(role_label, module, "Evidence review link", "")
        if html and "evidence/review" not in html and "ecs-evidence-review" not in html:
            if module in ("Frameworks", "AI SDLC Governance"):
                report.add(role_label, module, "Evidence link markup", "No evidence review triggers on page")
            else:
                report.add(role_label, module, "Evidence link markup", "")
    if spec.get("require_observation_links") and html:
        if "observation" in html.lower() or "close-obs" in html or "observation_id" in html:
            report.add(role_label, module, "Observation links", "")
        else:
            report.add(role_label, module, "Observation links", "No observation controls detected")


def validate_evidence_analytics_dashboard(role: str, role_label: str, module: str, report: CertReport):
    routes = _routes_for_module(module, role)
    for route in routes:
        html = validate_page_load(role, role_label, module, route, report)
        if MODULE_SPEC[module].get("require_kpi_macro") and html:
            if "ecs-kpi" not in html and "kpi_card" not in html and "ecs-exec-kpi" not in html:
                report.add(role_label, module, "Evidence Analytics KPIs", "No KPI cards on dashboard")
            else:
                report.add(role_label, module, "Evidence Analytics KPIs", "")
        validate_charts(role_label, module, html, report)
        validate_drilldowns_on_page(role, role_label, module, html, report)
        validate_popups(role_label, module, html, report)
        validate_evidence_observation_links(role, role_label, module, html, report)


def run_certification() -> CertReport:
    report = CertReport()
    for role_key, user, role_label in ROLES:
        for module in MODULE_SPEC:
            spec = MODULE_SPEC[module]
            if module == "Evidence Analytics":
                validate_evidence_analytics_dashboard(role_key, role_label, module, report)
                continue
            routes = _routes_for_module(module, role_key)
            nav_modules = spec.get("nav_modules", [])
            for i, route in enumerate(routes):
                html = validate_page_load(role_key, role_label, module, route, report)
                nav_mod = nav_modules[i] if i < len(nav_modules) else (nav_modules[0] if len(nav_modules) == 1 else "")
                if nav_mod:
                    validate_kpis(role_key, role_label, module, nav_mod, report)
                validate_charts(role_label, module, html, report)
                validate_drilldowns_on_page(role_key, role_label, module, html, report)
                validate_popups(role_label, module, html, report)
                validate_copilot(role_key, role_label, module, report)
                validate_evidence_observation_links(role_key, role_label, module, html, report)
            # Validate all nav_modules even if more than routes
            for nav_mod in nav_modules[len(routes) :]:
                validate_kpis(role_key, role_label, module, nav_mod, report)
    return report


def write_report(report: CertReport) -> Path:
    out_dir = ROOT / "modules" / "enterprise_grc" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "MODULE_FOCUS_CERTIFICATION_CIO_OWNER.csv"
    json_path = out_dir / "MODULE_FOCUS_CERTIFICATION_CIO_OWNER.json"

    fails = [f for f in report.findings if f.status == "FAIL"]
    passes = [f for f in report.findings if f.status == "PASS"]

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["Role", "Module", "Check", "Issue Found", "Issue Fixed", "Status"],
        )
        w.writeheader()
        for finding in report.findings:
            w.writerow({
                "Role": finding.role,
                "Module": finding.module,
                "Check": finding.check,
                "Issue Found": finding.issue,
                "Issue Fixed": finding.fixed,
                "Status": finding.status,
            })

    by_module: dict[str, dict] = {}
    for f in report.findings:
        key = f"{f.role}|{f.module}"
        if key not in by_module:
            by_module[key] = {"role": f.role, "module": f.module, "pass": 0, "fail": 0, "issues": []}
        if f.status == "FAIL":
            by_module[key]["fail"] += 1
            by_module[key]["issues"].append(f"{f.check}: {f.issue}")
        else:
            by_module[key]["pass"] += 1

    summary = {
        "certification": "PASS" if not fails else "FAIL",
        "certification_type": "MODULE_FOCUS_CIO_OWNER",
        "roles": ["CIO", "Application Owner"],
        "modules_validated": list(MODULE_SPEC.keys()),
        "checks_pass": len(passes),
        "checks_fail": len(fails),
        "issues_fixed": report.fixes_applied,
        "failures": [
            {
                "role": f.role,
                "module": f.module,
                "check": f.check,
                "issue": f.issue,
            }
            for f in fails
        ],
        "by_role_module": list(by_module.values()),
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return json_path


def main() -> int:
    print("=" * 72)
    print("MODULE-FOCUS CERTIFICATION — CIO + Application Owner")
    print("=" * 72)
    report = run_certification()
    path = write_report(report)
    fails = [f for f in report.findings if f.status == "FAIL"]
    print(f"Checks:  {len(report.findings)} ({len(report.findings) - len(fails)} pass, {len(fails)} fail)")
    print(f"Report:  {path.parent / 'MODULE_FOCUS_CERTIFICATION_CIO_OWNER.csv'}")
    print(f"Status:  {'PASS' if not fails else 'FAIL'}")
    if fails:
        print("\nFailures:")
        for f in fails[:25]:
            print(f"  [{f.role}] {f.module} — {f.check}: {f.issue}")
    print("=" * 72)
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
