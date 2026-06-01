#!/usr/bin/env python3
"""Full ECS demo readiness validation for Executive, Frameworks, Operations, Governance, GRC."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import ecs_state  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

ROLE = ("cio", "cio@bank.com")

PLACEHOLDER_RE = re.compile(
    r"\b(Lorem Ipsum|Mock Data|Sample Data|Dummy|coming soon)\b", re.I
)

MODULE_ROUTES: dict[str, list[str]] = {
    "Executive Overview": [
        "/mvp/demo-overview",
        "/mvp/enterprise",
        "/mvp/pan-india",
        "/mvp/reports",
        "/mvp/trends",
        "/dashboard/cio",
    ],
    "Frameworks": ["/mvp/framework-loader", "/mvp/framework-admin"],
    "Operations": [
        "/mvp/scheduler",
        "/mvp/ai-ops-assistant",
        "/mvp/upload",
        "/mvp/integrations",
        "/mvp/onboarding",
        "/mvp/integrations-hub",
    ],
    "Governance": [
        "/mvp/audit-prep",
        "/mvp/evidence-health",
        "/mvp/reuse",
        "/mvp/lifecycle",
        "/mvp/completeness",
        "/mvp/comparison",
        "/mvp/search",
        "/mvp/evidence-approval",
    ],
    "Enterprise GRC": [
        "/mvp/risk-register",
        "/mvp/exceptions",
        "/mvp/exception-governance",
        "/mvp/cmdb",
        "/mvp/regulatory",
        "/mvp/heatmaps",
        "/mvp/correlation",
        "/mvp/governance-analytics",
    ],
}


def _url(route: str) -> str:
    role, user = ROLE
    sep = "&" if "?" in route else "?"
    return f"{route}{sep}role={role}&user={user}"


def scan_pages() -> tuple[list[dict], int]:
    defects: list[dict] = []
    screens = 0
    for module, routes in MODULE_ROUTES.items():
        for route in routes:
            screens += 1
            resp = client.get(_url(route))
            if resp.status_code >= 500:
                defects.append(
                    {"severity": "P1", "module": module, "route": route, "issue": f"HTTP {resp.status_code}"}
                )
                continue
            if resp.status_code >= 400:
                defects.append(
                    {"severity": "P2", "module": module, "route": route, "issue": f"HTTP {resp.status_code}"}
                )
                continue
            if PLACEHOLDER_RE.search(resp.text):
                m = PLACEHOLDER_RE.search(resp.text)
                defects.append(
                    {
                        "severity": "P2",
                        "module": module,
                        "route": route,
                        "issue": f"Placeholder text: {m.group(0) if m else '?'}",
                    }
                )
            if resp.text.strip().startswith("{"):
                defects.append(
                    {"severity": "P1", "module": module, "route": route, "issue": "Raw JSON page"}
                )

    for fw in ecs_state.frameworks:
        screens += 1
        route = f"/framework/{quote(fw, safe='')}"
        resp = client.get(_url(route))
        if resp.status_code >= 500:
            defects.append(
                {"severity": "P1", "module": "Frameworks", "route": route, "issue": f"HTTP {resp.status_code}"}
            )
    return defects, screens


def run_sub_validators() -> list[str]:
    failures: list[str] = []
    scripts = [
        "scripts/validate_demo_engine.py",
        "scripts/validate_audit_prep.py",
        "scripts/validate_framework_loader.py",
    ]
    for script in scripts:
        proc = subprocess.run(
            [sys.executable, str(ROOT / script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            failures.append(f"{script} failed:\n{proc.stdout}\n{proc.stderr}")
    return failures


def main() -> int:
    defects, screens = scan_pages()
    sub_failures = run_sub_validators()

    p1 = sum(1 for d in defects if d["severity"] == "P1")
    p2 = sum(1 for d in defects if d["severity"] == "P2")
    p3 = sum(1 for d in defects if d["severity"] == "P3")

    print("=" * 60)
    print("ECS DEMO READINESS VALIDATION")
    print("=" * 60)
    print(f"Total screens assessed: {screens}")
    print(f"Defects found: {len(defects)} (P1={p1}, P2={p2}, P3={p3})")
    if defects:
        print("\nDefects:")
        for d in defects:
            print(f"  [{d['severity']}] {d['module']} {d['route']}: {d['issue']}")
    if sub_failures:
        print("\nSub-validator failures:")
        for f in sub_failures:
            print(f"  - {f.splitlines()[0]}")
        p1 += len(sub_failures)

    ready = p1 == 0 and not sub_failures
    print(f"\nDemo Readiness Status: {'READY' if ready else 'NOT READY'}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
