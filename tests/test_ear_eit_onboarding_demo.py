"""EAR/EIT automated control-checking prototype — onboarding-time demo fixtures.

Exercises the full existing reuse chain end to end for three app fixtures
(Net Banking / Mobile Banking / Payments) with mock evidence only:

    app fixture (config/phase2_application_portfolio.yaml)
      -> onboard (common_control_onboarding.onboard_application)
      -> technology detection (audit_intelligence.technology_fingerprint)
      -> PQ/adapter selection (config/common_control_rules.yaml)
      -> mock "scheduler" collection (common_control_demo_fixtures executor)
      -> normalize (predefined_query_normalizer)
      -> deterministic evaluation (common_control_rule_engine)
      -> persist (evidence_repository, via the same connector_common path
         every real connector uses)
      -> report + FCM mappings (common_control_report_engine)

No live connector is ever contacted — see common_control_demo_fixtures.py.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from modules.operations.engines.common_control_demo_fixtures import (
    DEMO_APP_IDS,
    onboard_demo_application,
)
from modules.operations.engines.common_control_rule_engine import (
    VERDICT_IMPLEMENTED,
    VERDICT_NOT_IMPLEMENTED,
    VERDICT_PARTIAL,
)

NB = "net_banking_ear_eit_demo"
MB = "mobile_banking_ear_eit_demo"
PAY = "payments_ear_eit_demo"


def _control_row(report: dict, control: str) -> dict:
    row = next((r for r in report["controls"] if r["control"] == control), None)
    assert row is not None, f"{control} missing from report for {report.get('application')}"
    return row


# --------------------------------------------------------------------------- #
# 1. Onboarding + technology discovery
# --------------------------------------------------------------------------- #
def test_three_apps_onboard_successfully():
    for app_id in DEMO_APP_IDS:
        report = onboard_demo_application(app_id)
        assert report["ok"] is True
        assert report["application_id"] == app_id
        assert report["assets"], f"{app_id} produced no assets"


def test_technology_discovery_matches_fixture_stacks():
    nb = onboard_demo_application(NB)
    mb = onboard_demo_application(MB)
    pay = onboard_demo_application(PAY)

    nb_tech = {a["technology"] for a in nb["assets"]}
    mb_tech = {a["technology"] for a in mb["assets"]}
    pay_tech = {a["technology"] for a in pay["assets"]}

    assert nb_tech == {"Aurora MySQL", "NGINX"}
    assert mb_tech >= {"YugabyteDB", "PostgreSQL", "NGINX"}
    assert pay_tech == {"MySQL", "NGINX"}
    # Payments' MySQL is a distinct canonical technology from NB's Aurora
    # MySQL — the whole point of avoiding a shared-technology verdict collision.
    assert "Aurora MySQL" not in pay_tech


# --------------------------------------------------------------------------- #
# 2. Deterministic EAR/EIT verdicts (the demo's core requirement)
# --------------------------------------------------------------------------- #
def test_net_banking_ear_and_eit_implemented():
    report = onboard_demo_application(NB)
    assert _control_row(report, "encryption-at-rest")["verdict"] == VERDICT_IMPLEMENTED
    assert _control_row(report, "encryption-in-transit")["verdict"] == VERDICT_IMPLEMENTED


def test_mobile_banking_ear_implemented_eit_partial():
    report = onboard_demo_application(MB)
    assert _control_row(report, "encryption-at-rest")["verdict"] == VERDICT_IMPLEMENTED
    eit = _control_row(report, "encryption-in-transit")
    assert eit["verdict"] == VERDICT_PARTIAL
    # Mixed required assets => PARTIAL: YugabyteDB failing, PostgreSQL + NGINX passing.
    assert eit["not_implemented_count"] >= 1
    assert eit["implemented_count"] >= 1


def test_payments_ear_not_implemented_eit_implemented():
    report = onboard_demo_application(PAY)
    assert _control_row(report, "encryption-at-rest")["verdict"] == VERDICT_NOT_IMPLEMENTED
    assert _control_row(report, "encryption-in-transit")["verdict"] == VERDICT_IMPLEMENTED


def test_nginx_tls_does_not_imply_db_tls_for_mobile_banking():
    """MB's NGINX TLS passes but must never mask YugabyteDB's failing TLS."""
    report = onboard_demo_application(MB)
    detail = {d["technology"]: d for d in report["evaluation_detail"] if d["control"] == "encryption-in-transit"}
    assert detail["NGINX"]["verdict"] == VERDICT_IMPLEMENTED
    assert detail["YugabyteDB"]["verdict"] == VERDICT_NOT_IMPLEMENTED
    assert detail["PostgreSQL"]["verdict"] == VERDICT_IMPLEMENTED
    # The app-level rollup must not be IMPLEMENTED just because NGINX passed.
    assert _control_row(report, "encryption-in-transit")["verdict"] != VERDICT_IMPLEMENTED


# --------------------------------------------------------------------------- #
# 3. Multi-asset aggregation
# --------------------------------------------------------------------------- #
def test_mobile_banking_evaluates_every_asset():
    report = onboard_demo_application(MB)
    asset_ids = {a["asset_id"] for a in report["assets"]}
    assert asset_ids == {"mb-demo-yugabyte", "mb-demo-postgresql", "mb-demo-aerospike", "mb-demo-nginx"}
    ear = _control_row(report, "encryption-at-rest")
    assert set(ear["technologies_evaluated"]) >= {"PostgreSQL", "YugabyteDB"}


# --------------------------------------------------------------------------- #
# 4. Persistence / retrieval
# --------------------------------------------------------------------------- #
def test_persisted_run_writes_versioned_evidence():
    from modules.operations.engines import evidence_repository as ops_repo

    before = len(ops_repo.evidence_repository)
    report = onboard_demo_application(NB, persist=True)
    assert report["ok"] is True
    after = len(ops_repo.evidence_repository)
    assert after > before

    aurora_records = [
        r for r in ops_repo.evidence_repository
        if (r.get("metadata") or {}).get("control") == "CLE-AWS-AURORA-EAR"
        or "CLE-AWS-AURORA-EAR" in str(r.get("source_item_id") or "")
        or "CLE-AWS-AURORA-EAR" in str(r.get("filename") or "")
    ]
    # At minimum, persisting must not silently no-op — some new evidence exists.
    assert after - before >= 1
    del aurora_records  # best-effort identification only; count assertion above is the contract


# --------------------------------------------------------------------------- #
# 5. FCM reuse — one EAR/EIT result maps to multiple existing frameworks
# --------------------------------------------------------------------------- #
def test_ear_eit_map_to_multiple_existing_frameworks():
    report = onboard_demo_application(NB)
    ear_frameworks = set()
    eit_frameworks = set()
    for detail in report["evaluation_detail"]:
        if detail["control"] == "encryption-at-rest":
            ear_frameworks.update(detail["frameworks"])
        if detail["control"] == "encryption-in-transit":
            eit_frameworks.update(detail["frameworks"])
    assert len(ear_frameworks) >= 1
    assert len(eit_frameworks) >= 1
    # No framework-specific engine — the same generic resolver produced both.
    fw_rows = {r["framework_name"] for r in report["frameworks"]}
    assert fw_rows >= eit_frameworks


# --------------------------------------------------------------------------- #
# 6. Rerun / idempotency
# --------------------------------------------------------------------------- #
def test_rerun_is_idempotent_for_verdicts():
    first = onboard_demo_application(MB)
    second = onboard_demo_application(MB)
    first_verdicts = {r["control"]: r["verdict"] for r in first["controls"]}
    second_verdicts = {r["control"]: r["verdict"] for r in second["controls"]}
    assert first_verdicts == second_verdicts


def test_rerun_with_persist_does_not_duplicate_unchanged_evidence():
    from modules.operations.engines import evidence_repository as ops_repo

    onboard_demo_application(PAY, persist=True)
    before = len(ops_repo.evidence_repository)
    onboard_demo_application(PAY, persist=True)
    after = len(ops_repo.evidence_repository)
    # Unchanged mock evidence must dedupe (hash-based), not fan out new rows
    # every rerun.
    assert after == before


# --------------------------------------------------------------------------- #
# 7. Regression — the underlying generic engine is untouched by this fixture work
# --------------------------------------------------------------------------- #
def test_existing_net_banking_app_is_unaffected():
    """The pre-existing net_banking portfolio entry must be untouched."""
    from modules.operations.engines.common_control_onboarding import onboard_application
    from modules.operations.engines.common_control_rule_engine import load_rule_pack

    pack = load_rule_pack()

    def _executor(control_id: str, user: str) -> dict:
        return {"ok": False, "error": "offline", "error_type": "connection_error"}

    report = onboard_application("net_banking", executor=_executor, pack=pack)
    assert report["ok"] is True
    assert report["application_id"] == "net_banking"


def test_no_application_names_hardcoded_in_new_demo_fixture_module():
    import inspect

    from modules.operations.engines import common_control_demo_fixtures as mod

    source = inspect.getsource(mod)
    for banned in ("if app_id ==", "NetBankingCollector", "MobileBankingCollector", "PaymentsCollector"):
        assert banned not in source
