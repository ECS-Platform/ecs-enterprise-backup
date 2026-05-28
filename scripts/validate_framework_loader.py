"""End-to-end smoke test for the Framework Loader feature."""

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
    ("vertical_head", "vertical.head@bank.com"),
]


def main() -> int:
    client = TestClient(app, raise_server_exceptions=False)
    failures: list[str] = []

    # 1. Loader page renders for every role
    for role, user in ROLES:
        url = f"/mvp/framework-loader?role={role}&user={user}"
        resp = client.get(url)
        if resp.status_code >= 500:
            failures.append(f"GET {url}: {resp.status_code}")

    # 2. Upload a new framework via the executive form (no file → uses mock CSV)
    upload_resp = client.post(
        "/mvp/framework-loader/upload",
        data={
            "framework_name": "DemoFrameworkQ2",
            "framework_type": "Pre-Assessment",
            "framework_owner": "Compliance Office",
            "role": "cio",
            "user": "cio@bank.com",
        },
    )
    if upload_resp.status_code >= 400:
        failures.append(f"POST upload: {upload_resp.status_code} — {upload_resp.text[:200]}")
        return _report(failures)

    payload = upload_resp.json()
    if not payload.get("ok") or not payload.get("framework_id"):
        failures.append(f"POST upload bad payload: {payload}")
        return _report(failures)

    framework_id = payload["framework_id"]
    print(f"Uploaded framework: {framework_id} → {payload.get('framework_name')}")

    # 3. Selected framework view loads with parsed controls
    sel_resp = client.get(
        f"/mvp/framework-loader?role=cio&user=cio@bank.com&framework_id={framework_id}"
    )
    if sel_resp.status_code != 200:
        failures.append(f"GET selected: {sel_resp.status_code}")
    elif b"Parsed Controls" not in sel_resp.content:
        failures.append("Parsed Controls block missing from selected view")

    # 4. Activate framework — should redirect 303 → loader page → become Active
    activate_resp = client.post(
        "/mvp/framework-loader/activate",
        data={"framework_id": framework_id, "role": "cio", "user": "cio@bank.com"},
        follow_redirects=True,
    )
    if activate_resp.status_code >= 400:
        failures.append(f"POST activate: {activate_resp.status_code}")
    elif b"Active" not in activate_resp.content:
        failures.append("Activated framework not visible in loader UI")

    # 5. Confirm framework now exists in the global registry (visible under
    #    Frameworks left nav). The catalog injection happens in _activate_framework.
    from app import ecs_state

    if "DemoFrameworkQ2" not in ecs_state.frameworks and "DemoFrameworkQ2" not in ecs_state.dynamic_framework_catalog:
        failures.append("Framework DemoFrameworkQ2 not registered post-activation")

    # 6. Open the auto-generated framework dashboard
    fw_resp = client.get("/framework/DemoFrameworkQ2?role=cio&user=cio@bank.com")
    if fw_resp.status_code >= 500:
        failures.append(f"GET /framework/DemoFrameworkQ2: {fw_resp.status_code}")

    # 7. Verify the new intelligence sections render in the page HTML
    intel_resp = client.get("/mvp/framework-loader?role=cio&user=cio@bank.com")
    expected_sections = [
        b"Evidence Reuse Dashboard",
        b"Cross-Framework Control Overlap Matrix",
        b"Control Theme Heatmap",
        b"Reuse Traceability",
        b"Application Evidence Scan",
    ]
    for needle in expected_sections:
        if needle not in intel_resp.content:
            failures.append(f"Loader page missing section: {needle.decode()}")

    # 8. Drill-down API for a known reusable theme
    drill_resp = client.get(
        "/api/framework-loader/control-drill?theme=encryption_rest"
    )
    if drill_resp.status_code != 200:
        failures.append(f"Drill-down API status: {drill_resp.status_code}")
    else:
        body = drill_resp.json()
        if not body.get("ok"):
            failures.append(f"Drill-down API payload: {body}")
        elif not body.get("linked_frameworks"):
            failures.append("Drill-down API returned no linked frameworks")
        elif not body.get("linked_evidence"):
            failures.append("Drill-down API returned no linked evidence")

    # 9. Unknown theme drill returns 404 cleanly
    unknown_resp = client.get("/api/framework-loader/control-drill?theme=does_not_exist")
    if unknown_resp.status_code != 404:
        failures.append(f"Unknown drill should 404, got {unknown_resp.status_code}")

    # 10. Application scan API
    app_resp = client.get("/api/framework-loader/application-scan")
    if app_resp.status_code != 200:
        failures.append(f"App scan API status: {app_resp.status_code}")
    elif not app_resp.json().get("rows"):
        failures.append("App scan API returned empty rows")

    return _report(failures)


def _report(failures: list[str]) -> int:
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("\nFramework Loader end-to-end smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
