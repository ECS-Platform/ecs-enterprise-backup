#!/usr/bin/env python3
"""Post-migration validation — routes, nav, drills, workflows."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

ROLES = ["cio", "owner", "auditor"]
MVP_PAGES = [
    "scheduler", "audit-prep", "evidence-health", "completeness", "search",
    "risk-register", "governance-analytics", "ai-ops-assistant", "bulk-upload",
    "onboarding", "reuse", "lifecycle", "comparison", "reports", "trends",
    "demo-overview", "enterprise", "pan-india",
]
AI_SDLC_PAGES = [
    "ai-sdlc", "ai-sdlc/control-tower", "ai-sdlc/onboarding", "sdlc-gates",
    "ai-governance", "ai-registry",
]
FRAMEWORKS = ["PCI DSS", "VAPT", "RBI Cyber Security", "AppSec"]

failed: list[str] = []


def check(name: str, cond: bool, msg: str = ""):
    if not cond:
        failed.append(f"{name}: {msg}")


def main():
    # Routes count
    check("route_count", len(app.routes) >= 180, f"got {len(app.routes)}")

    # Dashboard
    for role in ROLES:
        path = "/dashboard" if role in ("owner", "auditor") else f"/dashboard/{role.replace('_', '-')}" if role != "cio" else "/dashboard/cio"
        if role == "owner" or role == "auditor":
            path = "/dashboard"
        elif role == "cio":
            path = "/dashboard/cio"
        elif role == "vertical_head":
            path = "/dashboard/vertical-head"
        else:
            path = "/dashboard/compliance-head" if role == "compliance_head" else "/dashboard"
        r = client.get(f"{path}?role={role}&user={role}@bank.com")
        check(f"dashboard_{role}", r.status_code == 200, str(r.status_code))

    # MVP pages + universal drill
    for page in MVP_PAGES:
        r = client.get(f"/mvp/{page}?role=cio&user=cio@bank.com")
        check(f"mvp_{page}", r.status_code == 200, str(r.status_code))
        if r.status_code == 200:
            check(f"drill_{page}", "ecsUniversalDrillModal" in r.text or "ecsModuleKpiDrillModal" in r.text, "no drill modal")

    # Nav groups
    r = client.get("/mvp/scheduler?role=cio&user=cio@bank.com")
    for label in ("Executive Overview", "Frameworks", "Operations", "Governance", "Enterprise GRC"):
        check(f"nav_{label}", label in r.text, "missing nav group")

    # Frameworks
    for fw in FRAMEWORKS:
        r = client.get(f"/framework/{fw.replace(' ', '%20')}?role=cio&user=cio@bank.com")
        check(f"framework_{fw}", r.status_code == 200, str(r.status_code))
        if r.status_code == 200:
            check(f"fw_drill_{fw}", "data-ecs-framework-kpi" in r.text, "no kpi drill")

    # AI SDLC
    for page in AI_SDLC_PAGES:
        r = client.get(f"/mvp/{page}?role=cio&user=cio@bank.com")
        check(f"aisdlc_{page}", r.status_code == 200, str(r.status_code))

    # Drill APIs
    apis = [
        "/api/ecs/universal-drill?scope=kpi&page=scheduler&metric=failed&count=30",
        "/api/ecs/workflow-drill?metric=submitted&role=cio&count=30",
        "/api/framework/kpi-drill?framework=VAPT&metric=open_vulnerabilities",
        "/api/module-kpi/drill?module=scheduler&metric=failed&role=cio",
        "/api/ai-sdlc/posture/drill?metric=readiness",
    ]
    for url in apis:
        r = client.get(url)
        if r.status_code != 200:
            check(f"api_{url[:40]}", False, str(r.status_code))
        else:
            d = r.json()
            check(f"api_rows_{url[:30]}", d.get("ok", True) and len(d.get("rows", [1])) >= 1, "bad response")

    # Evidence workflow
    r = client.get("/dashboard?role=cio&user=cio@bank.com")
    check("enterprise_wf_drill", "data-ecs-enterprise-wf-drill" in r.text or "data-ecs-framework-wf-drill" in r.text, "")

    # Module imports
    from modules.shared.services import ecs_state
    from modules.frameworks.engines import framework_catalog
    from modules.ai_sdlc.engines import ai_sdlc_control_tower_engine
    check("module_imports", bool(ecs_state.frameworks) and bool(framework_catalog.FRAMEWORK_CATALOG), "")

    print(f"VALIDATION: {'' if not failed else 'FAILED'}")
    print(f"  Passed checks with {len(failed)} failures")
    for f in failed[:25]:
        print(f"  FAIL: {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
