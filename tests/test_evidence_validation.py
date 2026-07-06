"""Tests for the Evidence Validation Engine (Milestone 2).

Deterministic and offline. Builds synthetic EvidenceRecords and asserts verdicts,
control status, evidence quality, and the compliance summary.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from modules.audit_intelligence.engines import evidence_validation as val
from modules.audit_intelligence.models import (
    CONTROL_STATUS_COMPLIANT,
    CONTROL_STATUS_NEEDS_REVIEW,
    CONTROL_STATUS_NON_COMPLIANT,
    CONTROL_STATUS_NOT_ASSESSED,
    STATUS_COMPLETED,
    STATUS_CONFIG_REQUIRED,
    STATUS_CONNECTOR_MISSING,
    STATUS_FAILED,
    EvidenceRecord,
    VERDICT_FAIL,
    VERDICT_NOT_APPLICABLE,
    VERDICT_PASS,
    VERDICT_WARNING,
)


def _rec(**kw) -> EvidenceRecord:
    base = dict(control_id="C-1", technology="NGINX", status=STATUS_COMPLETED, ok=True)
    base.update(kw)
    return EvidenceRecord(**base)


TLS_CONTROL = {"control_name": "NGINX TLS Protocol", "description": "Ensure TLS enabled", "query": "show ssl"}
INV_CONTROL = {"control_name": "NGINX Version", "description": "Report version", "query": "nginx -v"}


# --------------------------------------------------------------------------- #
# Verdict rules
# --------------------------------------------------------------------------- #
def test_not_configured_is_not_applicable():
    r = _rec(status=STATUS_CONNECTOR_MISSING, ok=False)
    out = val.validate_record(r)
    assert out.verdict == VERDICT_NOT_APPLICABLE
    assert out.control_status == CONTROL_STATUS_NOT_ASSESSED
    assert out.evidence_quality == 0.0


def test_config_required_is_not_applicable():
    out = val.validate_record(_rec(status=STATUS_CONFIG_REQUIRED, ok=False))
    assert out.verdict == VERDICT_NOT_APPLICABLE


def test_failed_execution_is_fail_noncompliant():
    out = val.validate_record(_rec(status=STATUS_FAILED, ok=False, message="conn refused"))
    assert out.verdict == VERDICT_FAIL
    assert out.control_status == CONTROL_STATUS_NON_COMPLIANT


def test_empty_output_is_warning():
    out = val.validate_record(_rec(rows_returned=0, output_excerpt=""))
    assert out.verdict == VERDICT_WARNING
    assert out.control_status == CONTROL_STATUS_NEEDS_REVIEW


def test_assertion_positive_signal_passes():
    r = _rec(rows_returned=1, output_excerpt="ssl = on; TLSv1.2 enabled", evidence_id="E1")
    out = val.validate_record(r, TLS_CONTROL)
    assert out.verdict == VERDICT_PASS
    assert out.control_status == CONTROL_STATUS_COMPLIANT
    assert out.rule_id == "assertion.positive_signal"


def test_assertion_negative_signal_fails():
    r = _rec(rows_returned=1, output_excerpt="ssl = off; disabled", evidence_id="E1")
    out = val.validate_record(r, TLS_CONTROL)
    assert out.verdict == VERDICT_FAIL
    assert out.control_status == CONTROL_STATUS_NON_COMPLIANT


def test_assertion_mixed_signal_warns():
    r = _rec(rows_returned=1, output_excerpt="TLSv1.2 enabled but sslv3 also enabled")
    out = val.validate_record(r, TLS_CONTROL)
    # 'enabled' positive + 'sslv3' negative -> mixed -> warning
    assert out.verdict == VERDICT_WARNING


def test_inventory_control_passes_when_evidenced():
    r = _rec(rows_returned=1, output_excerpt="nginx/1.25.3", evidence_id="E9")
    out = val.validate_record(r, INV_CONTROL)
    assert out.verdict == VERDICT_PASS
    assert out.rule_id == "inventory.evidence_captured"


# --------------------------------------------------------------------------- #
# Evidence quality
# --------------------------------------------------------------------------- #
def test_evidence_quality_scaling():
    poor = val.validate_record(_rec(status=STATUS_FAILED, ok=False))
    rich = val.validate_record(
        _rec(rows_returned=3, output_excerpt="enabled", evidence_id="E"), TLS_CONTROL
    )
    assert poor.evidence_quality < rich.evidence_quality
    assert rich.evidence_quality >= 0.9


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def test_compliance_summary_excludes_not_applicable():
    records = [
        _rec(control_id="P", rows_returned=1, output_excerpt="enabled", evidence_id="e"),
        _rec(control_id="F", status=STATUS_FAILED, ok=False),
        _rec(control_id="NA", status=STATUS_CONNECTOR_MISSING, ok=False),
    ]
    controls = {"P": TLS_CONTROL, "F": TLS_CONTROL, "NA": TLS_CONTROL}
    results = val.validate_records(records, controls)
    summary = val.compliance_summary(results)
    assert summary["total"] == 3
    assert summary["assessed"] == 2  # NA excluded
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["not_applicable"] == 1
    assert summary["compliance_percent"] == 50.0


def test_compliance_warning_counts_half():
    records = [
        _rec(control_id="P", rows_returned=1, output_excerpt="enabled", evidence_id="e"),
        _rec(control_id="W", rows_returned=0, output_excerpt=""),  # -> warning
    ]
    results = val.validate_records(records, {"P": TLS_CONTROL})
    summary = val.compliance_summary(results)
    # 1 pass + 0.5 warning over 2 assessed = 75%
    assert summary["compliance_percent"] == 75.0


def test_validation_result_serializable():
    out = val.validate_record(_rec(rows_returned=1, output_excerpt="enabled"), TLS_CONTROL)
    d = out.to_dict()
    assert d["control_id"] == "C-1"
    assert isinstance(d["frameworks"], list)
    assert isinstance(d["evidence_quality"], float)
