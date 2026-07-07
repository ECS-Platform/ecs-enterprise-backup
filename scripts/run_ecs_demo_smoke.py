#!/usr/bin/env python3
"""ECS demo smoke runner — verify the platform end-to-end with NO live dependencies.

Runs a deterministic, offline walkthrough of the ECS Audit Intelligence stack and
prints a clear PASS/FAIL summary suitable for a pre-demo check or CI smoke gate:

  1. predefined query catalog loads
  2. audit intelligence services import
  3. mocked asset discovery (ServiceNow mock transport)
  4. technology -> control mapping count
  5. evidence orchestration (mocked executor run)
  6. evidence validation summary
  7. observation generation count
  8. evidence pack manifest generation (+ verification)
  9. dashboard aggregation
 10. integration adapters registry + health (config-only)

No Docker, no DB, no network. Exit code 0 when all checks pass, 1 otherwise.

Usage:  python scripts/run_ecs_demo_smoke.py [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _servicenow_transport(method, url, headers, params):
    return {"result": [
        {"sys_id": "SNOW-1", "name": "svc-nginx-lb", "sys_class_name": "cmdb_ci_server", "used_for": "UAT"},
        {"sys_id": "SNOW-2", "name": "db-postgres-01", "sys_class_name": "cmdb_ci_server", "used_for": "UAT"},
    ]}


def _executor(control_id, user):
    if control_id == "NGX-005":
        return {"ok": True, "message": "ok", "rows_returned": 1, "output": "server_tokens off; disabled",
                "evidence_id": "E5", "evidence_filename": "e5.txt", "duration_ms": 3}
    return {"ok": True, "message": "ok", "rows_returned": 1, "output": "TLSv1.2 enabled",
            "evidence_id": f"E-{control_id}", "evidence_filename": "e.txt", "duration_ms": 3}


def run_smoke() -> dict:
    checks: list[dict] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    # 1. Predefined query catalog
    try:
        from modules.operations.engines import predefined_queries_engine as engine

        controls = engine.get_all_controls()
        record("predefined_query_catalog", len(controls) >= 100, f"{len(controls)} controls")
    except Exception as exc:  # noqa: BLE001
        record("predefined_query_catalog", False, f"{type(exc).__name__}: {exc}")

    # 2. Audit intelligence services import
    try:
        from modules.audit_intelligence.engines import (
            asset_discovery, evidence_orchestrator as orch, evidence_packs,
            evidence_repository as repo, evidence_validation as validation,
            observation_generation as obs, technology_control_mapping as mapping,
            technology_fingerprint as fp,
        )
        from modules.audit_intelligence.services import dashboard_service
        record("audit_intelligence_services_import", True, "all engines/services imported")
    except Exception as exc:  # noqa: BLE001
        record("audit_intelligence_services_import", False, f"{type(exc).__name__}: {exc}")
        return _summary(checks)

    for m in (mapping, fp):
        m.reset_cache()
    orch.reset_runs()
    repo.reset_repository()
    obs.reset_observations()

    # 3. Mocked asset discovery
    try:
        os.environ["ECS_SERVICENOW_BASE_URL"] = "https://demo.example.service-now.com"
        assets = asset_discovery.discover_from_servicenow(transport=_servicenow_transport)
        record("mocked_asset_discovery", len(assets) == 2,
               f"{len(assets)} assets ({', '.join(a.technology for a in assets)})")
    except Exception as exc:  # noqa: BLE001
        record("mocked_asset_discovery", False, f"{type(exc).__name__}: {exc}")

    # 4. Mapping count
    try:
        stats = mapping.mapping_stats()
        record("technology_control_mapping", stats["controls"] >= 100,
               f"{stats['technologies']} tech / {stats['controls']} controls / {stats['frameworks']} frameworks")
    except Exception as exc:  # noqa: BLE001
        record("technology_control_mapping", False, f"{type(exc).__name__}: {exc}")

    # 5. Evidence orchestration (mocked run)
    run = None
    try:
        run = orch.create_run(scope_kind="technology", scope_value="NGINX",
                              control_ids=["NGX-003", "NGX-005"], asset_id="SNOW-1")
        for rec in run.records:
            rec.executable = True
        orch.execute_run(run.run_id, executor=_executor)
        record("evidence_orchestration", run.status == "Completed",
               f"run {run.run_id} status={run.status}")
    except Exception as exc:  # noqa: BLE001
        record("evidence_orchestration", False, f"{type(exc).__name__}: {exc}")

    # 6. Validation summary
    results = []
    try:
        controls_by_id = {c.control_id: c.to_dict() for c in mapping.all_controls()}
        results = validation.validate_records(run.records, controls_by_id) if run else []
        summ = validation.compliance_summary(results)
        record("evidence_validation", summ["assessed"] >= 1,
               f"compliance={summ['compliance_percent']}% passed={summ['passed']} failed={summ['failed']}")
    except Exception as exc:  # noqa: BLE001
        record("evidence_validation", False, f"{type(exc).__name__}: {exc}")

    # 7. Observation generation
    try:
        observations = obs.generate_from_results(results, asset_id="SNOW-1")
        record("observation_generation", len(observations) == 1,
               f"{len(observations)} observation(s)")
    except Exception as exc:  # noqa: BLE001
        record("observation_generation", False, f"{type(exc).__name__}: {exc}")

    # 8. Evidence pack manifest
    try:
        repo.store_from_run(run, results_by_control={r.control_id: r for r in results})
        pack = evidence_packs.technology_pack("NGINX")
        verified = evidence_packs.verify_manifest(pack)
        record("evidence_pack_manifest", pack["item_count"] == 2 and verified,
               f"items={pack['item_count']} verified={verified} checksum={pack['pack_checksum']}")
    except Exception as exc:  # noqa: BLE001
        record("evidence_pack_manifest", False, f"{type(exc).__name__}: {exc}")

    # 9. Dashboard aggregation
    try:
        dash = dashboard_service.executive_readiness()
        record("dashboard_aggregation",
               dash["evidence_coverage"]["evidence_keys"] == 2 and dash["open_observations"]["total"] == 1,
               f"evidence_keys={dash['evidence_coverage']['evidence_keys']} "
               f"open_obs={dash['open_observations']['total']} risk={dash['risk_summary']['risk_band']}")
    except Exception as exc:  # noqa: BLE001
        record("dashboard_aggregation", False, f"{type(exc).__name__}: {exc}")

    # 10. Integration adapters
    try:
        from modules.operations import integrations

        h = integrations.health_check_all()
        # Authoritative baseline is 11 (incl. SharePoint/Teams/Outlook Graph).
        record("integration_adapters", h["total"] >= 11,
               f"{h['total']} adapters registered ({h['configured']} configured)")
    except Exception as exc:  # noqa: BLE001
        record("integration_adapters", False, f"{type(exc).__name__}: {exc}")

    return _summary(checks)


def _summary(checks: list[dict]) -> dict:
    passed = sum(1 for c in checks if c["ok"])
    return {"checks": checks, "passed": passed, "total": len(checks),
            "ok": passed == len(checks)}


def render(report: dict) -> str:
    lines = ["ECS Demo Smoke Check", "====================", ""]
    for c in report["checks"]:
        mark = "PASS" if c["ok"] else "FAIL"
        lines.append(f"  [{mark}] {c['check']:32} {c['detail']}")
    lines.append("")
    lines.append(f"Result: {report['passed']}/{report['total']} checks passed "
                 f"-> {'ALL PASS' if report['ok'] else 'FAILURES PRESENT'}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ECS demo smoke runner (no live deps).")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)
    report = run_smoke()
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
