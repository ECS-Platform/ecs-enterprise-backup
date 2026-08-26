"""Tests for the generic deterministic Common-Control Rule Engine.

Covers: technology -> PQ selection, PASS/FAIL/PARTIAL/UNKNOWN/NOT_APPLICABLE
verdicts, multiple-asset aggregation, common-control reuse across
technologies, FCM framework mapping (never claiming full framework
compliance), onboarding execution over the existing application/CMDB
portfolio, the ``POST /api/control-evaluation`` service contract, and a
regression check that the frozen Phase-1 CommonControls catalogue and the
predefined-query evidence publisher are unaffected.

No live connectors are used — every predefined-query execution is stubbed via
the engine's ``executor`` override, so these tests are fully offline and
deterministic.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.engines.common_control_evaluation_engine import (
    evaluate_common_control,
    evaluate_common_control_for_asset,
    evaluate_controls_for_assets,
    evaluate_controls_for_technology,
)
from modules.operations.engines.common_control_onboarding import (
    onboard_application,
    onboard_assets,
)
from modules.operations.engines.common_control_report_engine import (
    build_framework_coverage,
    build_implementation_report,
)
from modules.operations.engines.common_control_rule_engine import (
    VERDICT_IMPLEMENTED,
    VERDICT_NOT_APPLICABLE,
    VERDICT_NOT_IMPLEMENTED,
    VERDICT_PARTIAL,
    VERDICT_UNKNOWN,
    apply_operator,
    load_rule_pack,
)
from modules.operations.services.control_evaluation_service import evaluate_control_request


# --------------------------------------------------------------------------- #
# Fixture executors — deterministic, offline, no live connectors
# --------------------------------------------------------------------------- #
def _ok(output: str) -> dict:
    return {"ok": True, "output": output, "duration_ms": 5}


def _unreachable() -> dict:
    return {"ok": False, "error": "connection refused", "error_type": "connection_error"}


PG_ALL_PASS = {
    "PGX-001": _ok("ssl\n---\non"),
    "PGX-002": _ok("password_encryption\n-------------------\nscram-sha-256"),
    "PGX-004": _ok("rolname | rolsuper\n-------------------\npostgres | t"),
    "PGX-008": _ok("extname\n-------\npgaudit"),
    "PGX-013": _ok("name | setting\n--------------\nlog_connections | on\nlog_statement | ddl"),
}


def make_executor(fixtures: dict[str, dict]):
    def _run(control_id: str, user: str) -> dict:
        return fixtures.get(control_id, _unreachable())

    return _run


# --------------------------------------------------------------------------- #
# 1. Technology -> predefined-query selection
# --------------------------------------------------------------------------- #
def test_rule_pack_loads_and_indexes_by_control_and_technology():
    rp = load_rule_pack()
    assert rp.rules
    assert "encryption-in-transit" in rp.controls()
    assert "PostgreSQL" in rp.technologies_for_control("encryption-in-transit")
    assert "encryption-in-transit" in rp.controls_for_technology("PostgreSQL")


def test_predefined_query_ids_selected_per_technology_not_hardcoded():
    rp = load_rule_pack()
    pg_ids = rp.predefined_query_ids("audit-logging", "PostgreSQL")
    mysql_ids = rp.predefined_query_ids("audit-logging", "Aurora MySQL")
    assert pg_ids and mysql_ids
    assert set(pg_ids).isdisjoint(mysql_ids)
    assert all(pid.startswith("PGX") for pid in pg_ids)
    assert all(pid.startswith("MYX") for pid in mysql_ids)


def test_unmapped_technology_selects_no_queries():
    rp = load_rule_pack()
    assert rp.rules_for("encryption-in-transit", "Aerospike") == []
    # Tomcat has no encryption-at-rest rule (unlike PostgreSQL, which now has
    # a cloud-control-plane EAR rule — see EAR-CLOUD-POSTGRESQL).
    assert rp.predefined_query_ids("encryption-at-rest", "Tomcat") == []


# --------------------------------------------------------------------------- #
# 2. Operators
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "operator,actual,expected,result",
    [
        ("equals", "on", "on", True),
        ("equals", "ON", "on", True),
        ("not_equals", "off", "on", True),
        ("exists", "", None, False),
        ("exists", "value", None, True),
        ("gte", "5", 3, True),
        ("gte", "2", 3, False),
        ("lte", "2", 3, True),
        ("contains", "TLSv1.2 TLSv1.3", "tlsv1.2", True),
        ("not_contains", "TLSv1.2", "sslv3", True),
    ],
)
def test_apply_operator(operator, actual, expected, result):
    assert apply_operator(operator, actual, expected) is result


def test_apply_operator_rejects_unsupported_operator():
    with pytest.raises(ValueError):
        apply_operator("regex_match", "x", "y")


# --------------------------------------------------------------------------- #
# 3. PASS / FAIL / PARTIAL / UNKNOWN / NOT_APPLICABLE verdicts
# --------------------------------------------------------------------------- #
def test_verdict_implemented_when_all_rules_pass():
    ev = evaluate_common_control(
        "encryption-in-transit", "PostgreSQL", executor=make_executor(PG_ALL_PASS)
    )
    assert ev.verdict == VERDICT_IMPLEMENTED
    assert ev.rule_outcomes and all(o.status == "PASS" for o in ev.rule_outcomes)


def test_verdict_not_implemented_when_rule_fails():
    fixtures = dict(PG_ALL_PASS)
    fixtures["PGX-001"] = _ok("ssl\n---\noff")
    ev = evaluate_common_control("encryption-in-transit", "PostgreSQL", executor=make_executor(fixtures))
    assert ev.verdict == VERDICT_NOT_IMPLEMENTED
    assert ev.rule_outcomes[0].status == "FAIL"
    assert ev.rule_outcomes[0].actual_value == "off"


def test_verdict_partial_when_mixed_pass_and_fail_or_unknown():
    fixtures = {
        "PGX-008": _ok("extname\n-------\npgaudit"),          # PASS
        "PGX-013": _ok("name | setting\n--------------\nlog_connections | off\nlog_statement | none"),  # FAIL both
    }
    ev = evaluate_common_control("audit-logging", "PostgreSQL", executor=make_executor(fixtures))
    assert ev.verdict == VERDICT_PARTIAL
    statuses = {o.status for o in ev.rule_outcomes}
    assert "PASS" in statuses and "FAIL" in statuses


def test_verdict_unknown_when_evidence_missing_never_implemented():
    ev = evaluate_common_control("encryption-in-transit", "PostgreSQL", executor=make_executor({}))
    assert ev.verdict == VERDICT_UNKNOWN
    assert ev.verdict != VERDICT_IMPLEMENTED
    assert ev.rule_outcomes[0].reason_code == "CONNECTIVITY_PENDING"


def test_verdict_not_applicable_when_no_rule_for_technology():
    ev = evaluate_common_control("encryption-at-rest", "Tomcat", executor=make_executor({}))
    assert ev.verdict == VERDICT_NOT_APPLICABLE
    assert ev.rule_outcomes == []


def test_aggregation_all_fails_if_any_row_fails():
    fixtures = {
        "ORX-009": _ok(
            "tablespace_name | encrypted\n---------------------------\n"
            "USERS | YES\nSYSTEM | YES\nUNDOTBS1 | NO"
        )
    }
    rp = load_rule_pack()
    rules = [r for r in rp.rules_for("encryption-at-rest", "Oracle") if r.predefined_query_id == "ORX-009"]
    assert len(rules) == 1
    from modules.operations.engines.common_control_evaluation_engine import gather_evidence_for_rule
    from modules.operations.engines.common_control_rule_engine import evaluate_rule

    ev = gather_evidence_for_rule(rules[0], user="tester", executor=make_executor(fixtures))
    outcome = evaluate_rule(rules[0], ev)
    assert outcome.status == "FAIL"
    assert outcome.actual_value == ["NO"]


def test_empty_result_set_is_unknown_not_a_pass():
    """A query that returns zero rows is not proof of compliance."""
    ev = evaluate_common_control(
        "encryption-in-transit",
        "PostgreSQL",
        executor=make_executor({"PGX-001": _ok("(no output)")}),
    )
    assert ev.verdict == VERDICT_UNKNOWN


# --------------------------------------------------------------------------- #
# 4. Multiple assets
# --------------------------------------------------------------------------- #
def test_evaluate_controls_for_assets_across_multiple_assets():
    from modules.audit_intelligence.models import Asset

    assets = [
        Asset(asset_id="pg-1", technology="PostgreSQL", application="Demo", environment="UAT"),
        Asset(asset_id="pg-2", technology="PostgreSQL", application="Demo", environment="UAT"),
    ]
    # encryption-in-transit/PostgreSQL depends on exactly one PQ (PGX-001), so
    # each asset triggers exactly one executor call — alternate PASS/FAIL by
    # call order to prove the two assets are evaluated independently (the
    # engine has no per-asset connection target in Phase-1; a real per-asset
    # difference would come from the connector, not this test's stand-in).
    calls = {"n": 0}

    def executor(control_id, user):
        calls["n"] += 1
        fixtures = PG_ALL_PASS if calls["n"] == 1 else {"PGX-001": _ok("ssl\n---\noff")}
        return fixtures.get(control_id, _unreachable())

    evals = evaluate_controls_for_assets(["encryption-in-transit"], assets, executor=executor)
    by_asset = {e.asset_id: e for e in evals}
    assert set(by_asset) == {"pg-1", "pg-2"}
    assert by_asset["pg-1"].verdict == VERDICT_IMPLEMENTED
    assert by_asset["pg-2"].verdict == VERDICT_NOT_IMPLEMENTED


def test_pq_evidence_cached_within_one_asset_not_across_assets():
    """A PQ referenced by two rules for the same asset executes once; a second
    asset gets its own independent execution (different target)."""
    from modules.audit_intelligence.models import Asset

    assets = [
        Asset(asset_id="pg-1", technology="PostgreSQL"),
        Asset(asset_id="pg-2", technology="PostgreSQL"),
    ]
    calls: list[str] = []

    def executor(control_id, user):
        calls.append(control_id)
        return PG_ALL_PASS.get(control_id, _unreachable())

    evaluate_controls_for_assets(["audit-logging"], assets, executor=executor)
    # PGX-013 backs two audit-logging rules; must run once per asset, not twice.
    assert calls.count("PGX-013") == 2  # once per asset (pg-1, pg-2) — cache is per-asset, not global


# --------------------------------------------------------------------------- #
# 5. Common-control reuse across technologies (no per-app/tech branching)
# --------------------------------------------------------------------------- #
def test_same_control_evaluated_uniformly_across_technologies():
    """identity-privileged-access must use the same evaluation code path for
    every technology — only the rule pack differs, never the engine."""
    fixtures = {
        "PGX-004": _ok("rolname | rolsuper\n-------------------\npostgres | t"),
        "MYX-009": _ok("user | host | select_priv\n---------------------------\nadmin | % | Y"),
        "LNX-007": _ok("admin ALL=(ALL) ALL"),
        "LNX-008": _ok("root:0:/bin/bash"),
    }
    executor = make_executor(fixtures)
    pg = evaluate_common_control("identity-privileged-access", "PostgreSQL", executor=executor)
    mysql = evaluate_common_control("identity-privileged-access", "Aurora MySQL", executor=executor)
    linux = evaluate_common_control("identity-privileged-access", "Linux", executor=executor)
    for ev in (pg, mysql, linux):
        assert ev.verdict == VERDICT_IMPLEMENTED
        assert ev.control_id == "CC-IDENTITY_PRIVILEGED_ACCESS"  # same control identity everywhere


def test_no_application_or_technology_names_hardcoded_in_engine_source():
    import inspect

    from modules.operations.engines import common_control_evaluation_engine as eng

    src = inspect.getsource(eng)
    for banned in ("Net Banking", "Mobile Banking", "Payments", "netbanking", "mobile_banking"):
        assert banned not in src


# --------------------------------------------------------------------------- #
# 6. Framework mapping — never claim full framework compliance
# --------------------------------------------------------------------------- #
def test_framework_mapping_resolves_for_legacy_and_new_slugs():
    ev_legacy = evaluate_common_control("audit-logging", "PostgreSQL", executor=make_executor(PG_ALL_PASS))
    ev_new = evaluate_common_control("password-policy", "PostgreSQL", executor=make_executor(PG_ALL_PASS))
    assert any(m["framework_name"] == "PCI DSS" for m in ev_legacy.framework_mappings)
    assert any(m["framework_name"] == "ASST" for m in ev_new.framework_mappings)


def test_framework_coverage_not_claimed_compliant_from_partial_controls():
    fixtures = dict(PG_ALL_PASS)
    fixtures["PGX-013"] = _ok("name | setting\n--------------\nlog_connections | off\nlog_statement | none")
    evals = [
        evaluate_common_control("audit-logging", "PostgreSQL", executor=make_executor(fixtures)),
        evaluate_common_control("encryption-in-transit", "PostgreSQL", executor=make_executor(fixtures)),
    ]
    rows = build_framework_coverage(evals)
    pci = next(r for r in rows if r["framework_name"] == "PCI DSS")
    # audit-logging is PARTIAL for PCI, so PCI coverage must be < 100%, and the
    # report must show the partial count explicitly rather than rounding up.
    assert pci["coverage_pct"] < 100.0
    assert pci["partial"] >= 1
    assert pci["framework_control_count"] >= pci["controls_mapped"]


def test_implementation_report_never_marks_not_applicable_as_gap():
    evals = [evaluate_common_control("encryption-at-rest", "Tomcat", executor=make_executor({}))]
    report = build_implementation_report(evals)
    assert report["not_applicable"] and not report["unknown"] and not report["not_implemented"]
    assert report["coverage_denominator"] == "applicable common controls (NOT_APPLICABLE excluded)"


# --------------------------------------------------------------------------- #
# 7. Onboarding execution (existing application/CMDB portfolio)
# --------------------------------------------------------------------------- #
def test_onboard_application_unknown_app_does_not_crash():
    report = onboard_application("does_not_exist", executor=make_executor({}))
    assert report["ok"] is False
    assert "known_applications" in report


def test_onboard_application_continues_through_unreachable_assets():
    """Connectivity-unavailable assets must not stop onboarding of the rest."""
    report = onboard_application("net_banking", executor=make_executor({}))
    assert report["ok"] is True
    assert len(report["assets"]) == 3
    assert report["connectivity_pending"]
    assert VERDICT_IMPLEMENTED.lower() not in "".join(c["control"] for c in report["unknown"])
    assert all(row["verdict"] != VERDICT_IMPLEMENTED for row in report["unknown"] + report["not_applicable"])


def test_onboard_application_technology_canonicalized_from_portfolio_slug():
    """Portfolio config uses adapter slugs (aurora_mysql); the engine must
    canonicalize to the predefined-query catalog's technology label."""
    report = onboard_application("net_banking", executor=make_executor({}))
    techs = {a["technology"] for a in report["assets"]}
    assert techs == {"Aurora MySQL", "Linux", "NGINX"}


def test_onboard_application_config_only_new_app_requires_no_code_change():
    """demo_card_portal exists purely as config — proves generic onboarding."""
    report = onboard_application("demo_card_portal", executor=make_executor({}))
    assert report["ok"] is True
    assert {a["technology"] for a in report["assets"]} == {"PostgreSQL", "NGINX"}


def test_onboard_assets_generic_cmdb_path():
    from modules.audit_intelligence.models import Asset

    assets = [Asset(asset_id="a1", technology="PostgreSQL", application="X", environment="UAT")]
    report = onboard_assets(assets, controls=["encryption-in-transit"], executor=make_executor(PG_ALL_PASS))
    assert report["ok"] is True
    assert [c["control"] for c in report["implemented"]] == ["encryption-in-transit"]


# --------------------------------------------------------------------------- #
# 8. API report contract (POST /api/control-evaluation)
# --------------------------------------------------------------------------- #
def test_api_requires_application_id():
    resp = evaluate_control_request({})
    assert resp["ok"] is False
    assert resp["error_type"] == "missing_application_id"


def test_api_returns_required_fields_per_result():
    resp = evaluate_control_request(
        {"application_id": "net_banking", "control": "encryption-in-transit"},
        executor=make_executor({}),
    )
    assert resp["ok"] is True
    assert resp["results"]
    row = resp["results"][0]
    for key in ("control", "technology", "predefined_query_ids", "verdict", "reason", "frameworks"):
        assert key in row
    assert row["rule_results"]
    rule_row = row["rule_results"][0]
    for key in ("expected_value", "actual_value", "status", "evidence_id"):
        assert key in rule_row


def test_api_asset_filter_restricts_to_one_asset():
    resp = evaluate_control_request(
        {"application_id": "net_banking", "asset_id": "netbanking-nginx"}, executor=make_executor({})
    )
    assert resp["ok"] is True
    assert {r["asset_id"] for r in resp["results"]} == {"netbanking-nginx"}


def test_api_unknown_asset_filter_errors_cleanly():
    resp = evaluate_control_request(
        {"application_id": "net_banking", "asset_id": "does-not-exist"}, executor=make_executor({})
    )
    assert resp["ok"] is False
    assert resp["error_type"] == "unknown_asset"


def test_api_route_wiring_via_testclient():
    """End-to-end through the actual FastAPI route, when httpx is available."""
    try:
        from fastapi.testclient import TestClient
    except Exception as exc:  # noqa: BLE001 - environment-dependent optional dep
        pytest.skip(f"TestClient unavailable in this environment: {exc}")

    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/control-evaluation", json={"application_id": "net_banking"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["application_id"] == "net_banking"


# --------------------------------------------------------------------------- #
# 9. Regression — existing modules unaffected
# --------------------------------------------------------------------------- #
def test_frozen_phase1_common_controls_catalog_unchanged():
    from modules.operations.engines.common_controls_catalog import COMMON_CONTROLS

    assert len(COMMON_CONTROLS) == 10


def test_publisher_tabular_parser_still_handles_multi_column_output():
    from modules.operations.engines.predefined_query_publisher import _parse_tabular_output

    cols, rows = _parse_tabular_output("name | setting\n---------------\nssl | on\nfoo | bar")
    assert cols == ["name", "setting"]
    assert rows == [["ssl", "on"], ["foo", "bar"]]


def test_publisher_tabular_parser_now_handles_single_column_output():
    """Regression guard for the bug fixed alongside this feature: a
    single-column SQL result (e.g. ``SHOW ssl;``) previously parsed to
    nothing because the old parser required a `` | `` separator."""
    from modules.operations.engines.predefined_query_publisher import _parse_tabular_output

    cols, rows = _parse_tabular_output("ssl\n---\non")
    assert cols == ["ssl"]
    assert rows == [["on"]]


def test_publisher_ignores_non_tabular_shell_output():
    from modules.operations.engines.predefined_query_publisher import _parse_tabular_output

    cols, rows = _parse_tabular_output("PermitRootLogin no\nsome other line")
    assert cols == [] and rows == []
