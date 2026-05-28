"""End-to-end smoke test for the Audit Prep module."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


ROLES = [
    ("cio", "cio@bank.com"),
    ("admin", "admin@bank.com"),
    ("compliance_head", "compliance.head@bank.com"),
    ("auditor", "audit.lead@bank.com"),
    ("owner", "owner.app1@bank.com"),
]


def _report(failures: list[str]) -> int:
    if failures:
        print("\nAudit Prep smoke test failed:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nAudit Prep smoke test passed.")
    return 0


def main() -> int:
    client = TestClient(app, raise_server_exceptions=False)
    failures: list[str] = []

    # 1. Page renders cleanly for every role and includes the new sections.
    expected_sections = [
        b"Upcoming Audits",
        b"Audit Calendar",
        b"Audit Preparation Pipeline",
        b"Baselining History",
    ]
    for role, user in ROLES:
        url = f"/mvp/audit-prep?role={role}&user={user}"
        resp = client.get(url)
        if resp.status_code >= 500:
            failures.append(f"GET {url}: {resp.status_code}")
            continue
        for needle in expected_sections:
            if needle not in resp.content:
                failures.append(f"{role}: missing section {needle.decode()}")

    # 2. Selecting "All Frameworks" + "All Applications" should show every framework
    #    (the previous bug — table showed only PCI DSS).
    resp = client.get(
        "/mvp/audit-prep?role=cio&user=cio@bank.com&fw_filter=&app_filter="
    )
    body = resp.content
    expected_frameworks = [b"PCI DSS", b"DPSC", b"OS Baselining", b"DB Baselining",
                          b"Nginx Baselining", b"AppSec", b"VAPT", b"CSITE",
                          b"ITPP", b"ITDRM"]
    missing_fw = [fw.decode() for fw in expected_frameworks if fw not in body]
    if missing_fw:
        failures.append(f"All-frameworks view missing: {missing_fw}")

    # 3. Filter actually narrows results — only DPSC rows should remain.
    resp = client.get(
        "/mvp/audit-prep?role=cio&user=cio@bank.com&fw_filter=DPSC"
    )
    body = resp.content
    if b"DPSC" not in body:
        failures.append("DPSC filter view missing DPSC rows")
    # Quarterly-only frameworks should NOT appear in the upcoming-audits table
    # of a DPSC-filtered view (we still allow appearance in static reference
    # text; we look for the table cell <td>OS Baselining</td>).
    if b"<td>OS Baselining</td>" in body:
        failures.append("DPSC filter still includes OS Baselining rows in the audits table")

    # 4. KPI drill endpoint
    for metric in ("draft", "submitted", "reupload", "approval_rate",
                   "avg_review_time", "rejection_trend", "pending_aging"):
        kresp = client.get(f"/api/audit-prep/kpi-drill?metric={metric}")
        if kresp.status_code != 200:
            failures.append(f"KPI drill '{metric}' status {kresp.status_code}")
            continue
        payload = kresp.json()
        if not payload.get("ok") or "drill" not in payload:
            failures.append(f"KPI drill '{metric}' invalid payload")
            continue
        drill = payload["drill"]
        if "title" not in drill or "columns" not in drill or "rows" not in drill:
            failures.append(f"KPI drill '{metric}' missing keys")
        if drill.get("count", 0) <= 0:
            failures.append(f"KPI drill '{metric}' count is zero")

    # Unknown metric must 400
    bad = client.get("/api/audit-prep/kpi-drill?metric=unknown")
    if bad.status_code != 400:
        failures.append(f"Unknown KPI metric should 400, got {bad.status_code}")

    # 5. Audit detail endpoint
    upcoming_resp = client.get(
        "/api/audit-prep/upcoming?framework=&application=&risk=&status=&owner="
    )
    if upcoming_resp.status_code != 200:
        failures.append(f"Upcoming API status: {upcoming_resp.status_code}")
    else:
        payload = upcoming_resp.json()
        upcoming = payload.get("upcoming", [])
        if not upcoming:
            failures.append("Upcoming API returned no audits")
        else:
            audit_id = upcoming[0]["audit_id"]
            dresp = client.get(f"/api/audit-prep/audit-detail?audit_id={audit_id}")
            if dresp.status_code != 200 or not dresp.json().get("ok"):
                failures.append(f"Audit-detail endpoint failed for {audit_id}")
            else:
                detail = dresp.json()
                for key in ("audit", "controls", "drafts", "submitted", "reupload", "approved", "blockers"):
                    if key not in detail:
                        failures.append(f"Audit-detail missing key {key}")

        # Filter must work via API (DPSC only)
        dpsc_resp = client.get("/api/audit-prep/upcoming?framework=DPSC")
        if dpsc_resp.status_code != 200:
            failures.append(f"Upcoming?framework=DPSC: {dpsc_resp.status_code}")
        else:
            dpsc_payload = dpsc_resp.json()
            frameworks = {a["framework"] for a in dpsc_payload.get("upcoming", [])}
            if frameworks and frameworks != {"DPSC"}:
                failures.append(f"DPSC filter returned other frameworks: {frameworks}")
            if not dpsc_payload.get("upcoming"):
                failures.append("DPSC filter returned no audits")

    # Unknown audit id must 404
    bad = client.get("/api/audit-prep/audit-detail?audit_id=NOPE")
    if bad.status_code != 404:
        failures.append(f"Unknown audit id should 404, got {bad.status_code}")

    return _report(failures)


if __name__ == "__main__":
    raise SystemExit(main())
