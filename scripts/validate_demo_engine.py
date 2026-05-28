"""End-to-end smoke test for the ECS Enterprise Mock Data Engine."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


ROLES = [
    ("cio", "cio@bank.com"),
    ("compliance_head", "compliance.head@bank.com"),
    ("auditor", "audit.lead@bank.com"),
    ("owner", "owner.app1@bank.com"),
]


def _report(failures: list[str]) -> int:
    if failures:
        print("\nMock engine smoke test failed:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nMock engine smoke test passed.")
    return 0


def main() -> int:
    client = TestClient(app, raise_server_exceptions=False)
    failures: list[str] = []

    # 1. Demo overview page renders for every role and contains every section.
    expected_sections = [
        b"DEMO MODE ENABLED",
        b"Banking Applications Registry",
        b"Risk Heatmap",
        b"ServiceNow Tickets",
        b"AI Governance Posture",
        b"Multi-Year Audit History",
        b"VAPT Findings Dashboard",
        b"Baselining Drift Analytics",
        b"Evidence Lineage Tracking",
        b"Framework Catalogue",
        b"CIO Executive Snapshot",
    ]
    for role, user in ROLES:
        url = f"/mvp/demo-overview?role={role}&user={user}"
        resp = client.get(url)
        if resp.status_code >= 500:
            failures.append(f"GET {url}: {resp.status_code}")
            continue
        for needle in expected_sections:
            if needle not in resp.content:
                failures.append(f"{role}: missing section {needle.decode()}")

    # 2. Status + overview APIs respond ok with demo_mode=true
    status = client.get("/api/demo/status").json()
    if not status.get("ok") or not status.get("demo_mode"):
        failures.append(f"demo status payload: {status}")

    overview = client.get("/api/demo/overview").json()
    if not overview.get("ok"):
        failures.append("demo overview returned not ok")
    else:
        data = overview.get("data", {})
        for key in (
            "banking_applications", "frameworks", "servicenow_tickets",
            "ai_governance", "audit_history", "audit_history_summary",
            "risk_heatmap", "baselining_drift", "evidence_lineage",
            "vapt", "cio_executive",
        ):
            if not data.get(key):
                failures.append(f"overview missing/empty section: {key}")

    # 3. Each individual API returns ok + non-empty payload.
    endpoint_checks = [
        ("/api/demo/banking-applications", "rows"),
        ("/api/demo/frameworks", "rows"),
        ("/api/demo/servicenow", "rows"),
        ("/api/demo/ai-governance", "data"),
        ("/api/demo/prompt-audit", "rows"),
        ("/api/demo/hallucinations", "rows"),
        ("/api/demo/token-usage", "data"),
        ("/api/demo/audit-history", "rows"),
        ("/api/demo/risk-heatmap", "data"),
        ("/api/demo/drift", "data"),
        ("/api/demo/evidence-lineage", "rows"),
        ("/api/demo/vapt", "data"),
        ("/api/demo/cio-executive", "data"),
    ]
    for url, key in endpoint_checks:
        resp = client.get(url)
        if resp.status_code != 200:
            failures.append(f"GET {url}: {resp.status_code}")
            continue
        payload = resp.json()
        if not payload.get("ok"):
            failures.append(f"GET {url}: ok=false → {payload}")
            continue
        body = payload.get(key)
        if isinstance(body, list) and not body:
            failures.append(f"GET {url}: empty rows")
        elif isinstance(body, dict) and not body:
            failures.append(f"GET {url}: empty data")

    # 4. Banking applications count matches the registry expansion (≥18 apps)
    apps = client.get("/api/demo/banking-applications").json().get("rows", [])
    if len(apps) < 18:
        failures.append(f"Expected ≥18 banking apps, got {len(apps)}")
    expected_apps = {
        "Net Banking", "Mobile Banking", "UPI", "Payments", "Treasury",
        "Wealth Portal", "API Gateway", "Loan Origination", "Card Platform",
        "Internet Banking", "Retail Banking", "CBS Oracle", "Mobile Banking Edge",
        "Payment Switch", "AML Engine", "Fraud Monitoring", "Customer Onboarding",
        "Digital Lending", "Core Banking",
    }
    present = {a["application"] for a in apps}
    missing = expected_apps - present
    if missing:
        failures.append(f"Missing banking apps: {sorted(missing)}")

    # 5. Frameworks include the new ones (SOC2, ISO27001, RBI Cyber, ISG, ASST)
    fws = client.get("/api/demo/frameworks").json().get("rows", [])
    fw_names = {f["framework"] for f in fws}
    expected_new = {"SOC2", "ISO27001", "RBI Cyber Security", "ISG", "ASST"}
    missing_fws = expected_new - fw_names
    if missing_fws:
        failures.append(f"Missing frameworks: {sorted(missing_fws)}")

    # 6. ServiceNow tickets include all four ticket types
    snow = client.get("/api/demo/servicenow?limit=80").json().get("rows", [])
    types = {t["type"] for t in snow}
    if types != {"CHG", "INC", "PRB", "RITM"}:
        failures.append(f"ServiceNow tickets missing types: expected CHG/INC/PRB/RITM, got {sorted(types)}")

    # 7. ServiceNow type filter narrows results
    chg = client.get("/api/demo/servicenow?limit=80&type=CHG").json().get("rows", [])
    if chg and {t["type"] for t in chg} != {"CHG"}:
        failures.append("ServiceNow type=CHG filter returned other types")

    # 8. AI governance summary integrity
    ai = client.get("/api/demo/ai-governance").json().get("data", {})
    summary = ai.get("summary", {})
    if summary.get("prompts_audited", 0) <= 0:
        failures.append("AI governance prompts_audited == 0")

    # 9. Audit history spans 5 years
    hist = client.get("/api/demo/audit-history?years=5").json()
    years = {r["year"] for r in hist.get("rows", [])}
    if len(years) < 5:
        failures.append(f"Audit history years coverage: {sorted(years)}")

    # 10. VAPT findings include all severity tiers
    vapt = client.get("/api/demo/vapt").json().get("data", {})
    sev = vapt.get("severity_breakdown", {})
    for s in ("Critical", "High", "Medium", "Low"):
        if sev.get(s, 0) <= 0:
            failures.append(f"VAPT severity {s} has 0 findings")

    return _report(failures)


if __name__ == "__main__":
    raise SystemExit(main())
