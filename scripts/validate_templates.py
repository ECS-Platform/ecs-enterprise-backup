"""ECS Jinja Template Validation Engine.

Phase 8 deliverable. Runs three layers of validation:
1. Static parse — load every template through Jinja's parser to catch
   syntax errors, malformed expressions, broken includes/imports.
2. Macro contract audit — confirm the two corruption-prone macros in
   ``partials/ecs_ux_macros.html`` are loadable with either ``row`` or
   ``ev`` payloads without raising ``UndefinedError``.
3. Live route rendering — for every role x route combination defined
   in the app, fetch the page in-process via FastAPI's TestClient and
   assert the response status is < 500 (no template crashes).

Exit code is non-zero if any layer fails.
"""

from __future__ import annotations

import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEMPLATES_DIR = ROOT / "app" / "templates"

# ---------------------------------------------------------------------------
# Layer 1 — static parse + import resolution for every template file
# ---------------------------------------------------------------------------
from jinja2 import Environment, FileSystemLoader, StrictUndefined  # noqa: E402
from jinja2 import TemplateNotFound, TemplateSyntaxError  # noqa: E402

_FROM_IMPORT_RE = re.compile(
    r"""\{%-?\s*from\s+["']([^"']+)["']\s+import\s+([^%]+?)\s*-?%\}""",
    re.MULTILINE,
)
_INCLUDE_RE = re.compile(
    r"""\{%-?\s*include\s+["']([^"']+)["']""",
    re.MULTILINE,
)


def layer1_static_parse() -> list[str]:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    failures: list[str] = []
    files = sorted(TEMPLATES_DIR.rglob("*.html"))
    for file in files:
        rel = file.relative_to(TEMPLATES_DIR).as_posix()
        source = file.read_text(encoding="utf-8")
        try:
            env.parse(source)
        except TemplateSyntaxError as exc:
            failures.append(f"[parse] {rel}: line {exc.lineno}: {exc.message}")
            continue
        except Exception as exc:  # pragma: no cover
            failures.append(f"[parse] {rel}: {type(exc).__name__}: {exc}")
            continue

        for match in _INCLUDE_RE.finditer(source):
            target = match.group(1)
            try:
                env.get_template(target)
            except TemplateNotFound:
                failures.append(f"[include] {rel}: missing target '{target}'")

        for match in _FROM_IMPORT_RE.finditer(source):
            target, names_blob = match.group(1), match.group(2)
            wanted = [n.strip() for n in names_blob.split(",") if n.strip()]
            try:
                module = env.get_template(target).module
            except TemplateNotFound:
                failures.append(f"[import] {rel}: missing target '{target}'")
                continue
            for name in wanted:
                bare = name.split(" as ")[0].strip()
                if not hasattr(module, bare):
                    failures.append(
                        f"[import] {rel}: '{bare}' not exported by '{target}'"
                    )
    print(f"Layer 1 — parsed {len(files)} templates, {len(failures)} failure(s)")
    return failures


# ---------------------------------------------------------------------------
# Layer 2 — macro contract audit
# ---------------------------------------------------------------------------
def layer2_macro_contract() -> list[str]:
    failures: list[str] = []
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )

    # Provide template globals referenced by the macros
    def review_url(framework, control_name, eid, role, user, control_id):
        return (
            f"/mvp/evidence-approval?framework={framework}&control={control_name}"
            f"&evidence={eid}&role={role}&user={user}"
        )

    def review_url_for_ev(framework, ev, role, user):
        return (
            f"/mvp/evidence-approval?framework={framework}"
            f"&evidence={(ev or {}).get('evidence_id', '')}&role={role}&user={user}"
        )

    env.globals.update(review_url=review_url, review_url_for_ev=review_url_for_ev)

    macros = env.get_template("partials/ecs_ux_macros.html").module

    row_payloads = [
        {},
        {
            "control_id": "PCI-3.1",
            "control_name": "Encryption",
            "application": "Net Banking",
            "validation": "FAIL",
            "workflow_status": "Rejected",
            "owner": "alice",
            "risk": "Critical",
            "sla_aging_days": 30,
            "finding_count": 2,
            "finding_id": "OBS-101",
            "evidence_id": "EV-1",
            "observation_id": "OBS-101",
            "auditor_approved": False,
        },
        # Intentionally provide minimal/None-laced data
        {"control": "C-1", "application": None, "owner": None},
    ]

    ev_payloads = [
        {},
        {
            "control_id": "ISO-A.5.1",
            "control_name": "Policies",
            "application": "Mobile App",
            "lifecycle": "Approved",
            "validation": "Passed",
            "evidence_id": "EV-9",
            "auditor_approved": True,
            "observation_status": "Closed",
            "reuse_eligible": True,
            "observation_id": "OBS-9",
        },
        {"control": "C-2"},
    ]

    roles = ["auditor", "owner", "compliance_head", "cio", "vertical_head", "admin"]

    for role in roles:
        for idx, payload in enumerate(row_payloads):
            try:
                macros.governance_action_menu(idx, "PCI DSS", role, "demo", payload)
            except Exception as exc:
                failures.append(
                    f"[macro] governance_action_menu role={role} payload#{idx}: "
                    f"{type(exc).__name__}: {exc}"
                )
        for idx, payload in enumerate(ev_payloads):
            try:
                macros.evidence_action_menu(idx, "PCI DSS", role, "demo", payload)
            except Exception as exc:
                failures.append(
                    f"[macro] evidence_action_menu role={role} payload#{idx}: "
                    f"{type(exc).__name__}: {exc}"
                )

    # Strict-undefined sanity for safe_get / empty_state
    strict_env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
        undefined=StrictUndefined,
    )
    strict_env.globals.update(review_url=review_url, review_url_for_ev=review_url_for_ev)
    strict_macros = strict_env.get_template("partials/ecs_ux_macros.html").module
    try:
        strict_macros.empty_state()
        strict_macros.empty_state("Nothing here")
    except Exception as exc:
        failures.append(f"[macro] empty_state: {type(exc).__name__}: {exc}")

    print(f"Layer 2 — macro contracts checked, {len(failures)} failure(s)")
    return failures


# ---------------------------------------------------------------------------
# Layer 3 — live route render via FastAPI TestClient
# ---------------------------------------------------------------------------
def layer3_route_render() -> list[str]:
    failures: list[str] = []
    try:
        from fastapi.testclient import TestClient

        from app.main import app  # type: ignore
    except Exception as exc:
        failures.append(f"[route] FastAPI bootstrap failed: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return failures

    client = TestClient(app, raise_server_exceptions=False)

    roles_users = [
        ("auditor", "audit.lead@bank.com"),
        ("owner", "owner.app1@bank.com"),
        ("compliance_head", "compliance.head@bank.com"),
        ("cio", "cio@bank.com"),
        ("vertical_head", "vertical.head@bank.com"),
        ("admin", "admin@bank.com"),
    ]

    routes_to_test = [
        "/dashboard",
        "/mvp/enterprise",
        "/mvp/pan-india",
        "/mvp/trends",
        "/mvp/audit-prep",
        "/mvp/heatmaps",
        "/mvp/regulatory",
        "/mvp/correlation",
        "/mvp/exceptions",
        "/mvp/risk-register",
        "/mvp/reports",
        "/mvp/scheduler",
        "/mvp/lifecycle",
        "/mvp/governance-analytics",
        "/mvp/evidence-approval",
        "/mvp/evidence-health",
        "/mvp/completeness",
        "/mvp/comparison",
        "/mvp/cmdb",
        "/mvp/reuse",
        "/mvp/integrations",
        "/mvp/integrations-hub",
        "/mvp/onboarding",
        "/mvp/exception-governance",
        "/mvp/bulk-upload",
        "/mvp/framework-admin",
        "/mvp/framework-loader",
        "/mvp/search",
        "/framework/PCI%20DSS",
        "/framework/ISO%2027001",
        "/framework/RBI%20IT%20Framework",
        "/framework/SOC%202",
    ]

    total = 0
    for role, user in roles_users:
        for route in routes_to_test:
            sep = "&" if "?" in route else "?"
            url = f"{route}{sep}role={role}&user={user}"
            try:
                resp = client.get(url)
            except Exception as exc:
                failures.append(f"[route] {role} {url}: raised {type(exc).__name__}: {exc}")
                continue
            total += 1
            if resp.status_code >= 500:
                snippet = resp.text[:240].replace("\n", " ")
                failures.append(f"[route] {role} {url}: {resp.status_code} :: {snippet}")

    # ── Evidence repository workflow check ─────────────────────────────
    sample_evidence_ids = ["EV-SYNTH", "EV-1", "EV-9"]
    for role, user in roles_users:
        for eid in sample_evidence_ids:
            url = (
                f"/evidence/review?framework_name=PCI+DSS&evidence_id={eid}"
                f"&control_name=Encryption&role={role}&user={user}"
            )
            try:
                resp = client.get(url)
            except Exception as exc:
                failures.append(f"[evidence] {role} {url}: raised {type(exc).__name__}: {exc}")
                continue
            total += 1
            if resp.status_code >= 500:
                snippet = resp.text[:240].replace("\n", " ")
                failures.append(f"[evidence] {role} {url}: {resp.status_code} :: {snippet}")

    # ── Evidence repository POST round-trip (redirect targets render) ──
    post_targets = [
        "/evidence/review/submit",
        "/evidence/review/approve",
        "/evidence/review/reject",
        "/evidence/review/clarify",
        "/evidence/review/save-draft",
        "/evidence/review/close-observation",
    ]
    base_post_payload = {
        "framework_name": "PCI DSS",
        "control_name": "Encryption",
        "evidence_id": "EV-SYNTH",
    }
    for role, user in roles_users:
        for endpoint in post_targets:
            payload = dict(base_post_payload, role=role, user=user)
            if endpoint == "/evidence/review/reject":
                payload["reject_reason"] = "Synthetic validation reason"
            if endpoint == "/evidence/review/clarify":
                payload["message"] = "Synthetic validation clarification"
            if endpoint == "/evidence/review/save-draft":
                payload["owner_note"] = "Synthetic draft"
            if endpoint == "/evidence/review/close-observation":
                payload["observation_id"] = "OBS-SYNTH"
            try:
                resp = client.post(endpoint, data=payload, follow_redirects=True)
            except Exception as exc:
                failures.append(f"[evidence-post] {role} {endpoint}: raised {type(exc).__name__}: {exc}")
                continue
            total += 1
            if resp.status_code >= 500:
                snippet = resp.text[:240].replace("\n", " ")
                failures.append(f"[evidence-post] {role} {endpoint}: {resp.status_code} :: {snippet}")

    print(f"Layer 3 — fetched {total} role x route combos, {len(failures)} failure(s)")
    return failures


def main() -> int:
    all_failures: list[str] = []
    all_failures += layer1_static_parse()
    all_failures += layer2_macro_contract()
    all_failures += layer3_route_render()
    if all_failures:
        print("\n=== VALIDATION FAILURES ===")
        for f in all_failures:
            print(f)
        return 1
    print("\nAll template validation layers passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
