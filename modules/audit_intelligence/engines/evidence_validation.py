"""Evidence Validation Engine (Milestone 2).

Deterministically validates the evidence captured by the orchestrator and turns it
into audit-meaningful verdicts and scores:

  * verdict:         PASS | FAIL | WARNING | NOT APPLICABLE
  * control_status:  Compliant | Non-Compliant | Needs Review | Not Assessed
  * evidence_quality: 0.0 .. 1.0  (was evidence actually captured, with content?)
  * compliance %:    aggregate over a set of validations
  * evidence quality score: aggregate over a set of validations

Design:
  * 100% deterministic and rule-based — NO LLM dependency (per spec).
  * Rules inspect the normalized evidence (status, output excerpt, rows, error) plus
    lightweight keyword expectations derived from the control (e.g. TLS/encryption/
    audit/MFA controls expect an "enabled/on" signal). Rules are data-driven and
    extensible without touching the engine.
  * Operates on the frozen/serializable models; never touches connectors or secrets.
"""

from __future__ import annotations

import re
from typing import Any

from modules.audit_intelligence.models import (
    CONTROL_STATUS_COMPLIANT,
    CONTROL_STATUS_NEEDS_REVIEW,
    CONTROL_STATUS_NON_COMPLIANT,
    CONTROL_STATUS_NOT_ASSESSED,
    STATUS_COMPLETED,
    STATUS_CONNECTOR_MISSING,
    STATUS_CONFIG_REQUIRED,
    EvidenceRecord,
    ValidationResult,
    VERDICT_FAIL,
    VERDICT_NOT_APPLICABLE,
    VERDICT_PASS,
    VERDICT_WARNING,
)

# Positive signals that indicate a security control is satisfied.
_POSITIVE_PATTERNS = [
    r"\benabled\b", r"\bon\b", r"\btrue\b", r"\byes\b", r"\brequired\b",
    r"\bactive\b", r"\benforced\b", r"scram-sha-256", r"tlsv1\.[23]",
    r"require_secure_transport\s*[:=]?\s*on",
]
# Negative signals that indicate a control is NOT satisfied.
_NEGATIVE_PATTERNS = [
    r"\bdisabled\b", r"\boff\b", r"\bfalse\b", r"\bno\b(?!\w)", r"\bnot\s+enabled\b",
    r"\bnone\b", r"\bmd5\b", r"tlsv1\.0", r"tlsv1\.1", r"sslv3",
]

#: Control name/description keywords that mark a control as an "assertion" check
#: (its evidence is expected to show a positive/enabled state).
_ASSERTION_KEYWORDS = (
    "tls", "ssl", "encrypt", "encryption", "audit", "logging", "mfa",
    "secure", "password_encryption", "require", "cipher", "protocol",
)


def _control_keywords(control: dict[str, Any] | None) -> str:
    if not control:
        return ""
    return " ".join(
        str(control.get(k) or "") for k in ("control_name", "description", "category", "query")
    ).lower()


def _is_assertion_control(control_text: str) -> bool:
    return any(kw in control_text for kw in _ASSERTION_KEYWORDS)


def _match_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def validate_record(
    record: EvidenceRecord,
    control: dict[str, Any] | None = None,
) -> ValidationResult:
    """Validate one evidence record deterministically.

    ``control`` (optional) supplies the control metadata used for keyword-based
    expectations; if omitted, only the evidence status/output drives the verdict.
    """
    frameworks = tuple(record.frameworks)
    base = dict(
        control_id=record.control_id,
        technology=record.technology,
        frameworks=frameworks,
    )

    # 1. No usable evidence -> NOT APPLICABLE / not assessed.
    if record.status in (STATUS_CONNECTOR_MISSING, STATUS_CONFIG_REQUIRED):
        return ValidationResult(
            **base,
            verdict=VERDICT_NOT_APPLICABLE,
            control_status=CONTROL_STATUS_NOT_ASSESSED,
            evidence_quality=0.0,
            rule_id="no_evidence.not_configured",
            rationale=f"No evidence collected (status={record.status}).",
        )
    if not record.ok or record.status != STATUS_COMPLETED:
        return ValidationResult(
            **base,
            verdict=VERDICT_FAIL,
            control_status=CONTROL_STATUS_NON_COMPLIANT,
            evidence_quality=_evidence_quality(record),
            rule_id="execution.failed",
            rationale=record.message or "Evidence collection failed.",
        )

    output = (record.output_excerpt or "").lower()
    control_text = _control_keywords(control)
    quality = _evidence_quality(record)

    # 2. Completed but empty output -> WARNING (evidence exists but is thin).
    if not output and record.rows_returned == 0:
        return ValidationResult(
            **base,
            verdict=VERDICT_WARNING,
            control_status=CONTROL_STATUS_NEEDS_REVIEW,
            evidence_quality=quality,
            rule_id="content.empty",
            rationale="Executed successfully but returned no output rows.",
        )

    # 3. Assertion controls: look for positive/negative state in the evidence.
    if _is_assertion_control(control_text) or _match_any(_POSITIVE_PATTERNS + _NEGATIVE_PATTERNS, output):
        has_negative = _match_any(_NEGATIVE_PATTERNS, output)
        has_positive = _match_any(_POSITIVE_PATTERNS, output)
        if has_negative and not has_positive:
            return ValidationResult(
                **base,
                verdict=VERDICT_FAIL,
                control_status=CONTROL_STATUS_NON_COMPLIANT,
                evidence_quality=quality,
                rule_id="assertion.negative_signal",
                rationale="Evidence indicates the control is disabled/not enforced.",
            )
        if has_positive and not has_negative:
            return ValidationResult(
                **base,
                verdict=VERDICT_PASS,
                control_status=CONTROL_STATUS_COMPLIANT,
                evidence_quality=quality,
                rule_id="assertion.positive_signal",
                rationale="Evidence indicates the control is enabled/enforced.",
            )
        if has_positive and has_negative:
            return ValidationResult(
                **base,
                verdict=VERDICT_WARNING,
                control_status=CONTROL_STATUS_NEEDS_REVIEW,
                evidence_quality=quality,
                rule_id="assertion.mixed_signal",
                rationale="Evidence shows both enabled and disabled signals; manual review needed.",
            )
        # Assertion control but no clear signal -> needs review.
        return ValidationResult(
            **base,
            verdict=VERDICT_WARNING,
            control_status=CONTROL_STATUS_NEEDS_REVIEW,
            evidence_quality=quality,
            rule_id="assertion.no_signal",
            rationale="Assertion control returned evidence without a clear enabled/disabled signal.",
        )

    # 4. Inventory/enumeration controls: evidence captured -> PASS (compliant that
    #    the control was evidenced). These are informational baselines.
    return ValidationResult(
        **base,
        verdict=VERDICT_PASS,
        control_status=CONTROL_STATUS_COMPLIANT,
        evidence_quality=quality,
        rule_id="inventory.evidence_captured",
        rationale=f"Evidence captured ({record.rows_returned} row(s)).",
    )


def _evidence_quality(record: EvidenceRecord) -> float:
    """Score 0..1 for how substantive the captured evidence is."""
    if record.status in (STATUS_CONNECTOR_MISSING, STATUS_CONFIG_REQUIRED):
        return 0.0
    if not record.ok:
        return 0.1
    score = 0.5  # executed successfully
    if record.rows_returned > 0:
        score += 0.2
    if record.output_excerpt:
        score += 0.2
    if record.evidence_id:  # an evidence artifact was stored
        score += 0.1
    return min(score, 1.0)


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def validate_records(
    records: list[EvidenceRecord],
    controls_by_id: dict[str, dict[str, Any]] | None = None,
) -> list[ValidationResult]:
    """Validate a list of records (optionally supplying control metadata by id)."""
    controls_by_id = controls_by_id or {}
    return [validate_record(r, controls_by_id.get(r.control_id)) for r in records]


def compliance_summary(results: list[ValidationResult]) -> dict[str, Any]:
    """Compliance %, evidence-quality score, and verdict/status breakdowns.

    ``compliance_percent`` is computed over ASSESSED controls only (PASS/FAIL/
    WARNING), excluding NOT APPLICABLE, so unconfigured targets don't distort it.
    """
    total = len(results)
    verdicts: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for r in results:
        verdicts[r.verdict] = verdicts.get(r.verdict, 0) + 1
        statuses[r.control_status] = statuses.get(r.control_status, 0) + 1

    passed = verdicts.get(VERDICT_PASS, 0)
    failed = verdicts.get(VERDICT_FAIL, 0)
    warned = verdicts.get(VERDICT_WARNING, 0)
    not_applicable = verdicts.get(VERDICT_NOT_APPLICABLE, 0)
    assessed = passed + failed + warned

    # PASS counts fully; WARNING counts half toward compliance.
    compliance = ((passed + 0.5 * warned) / assessed) if assessed else 0.0
    avg_quality = (sum(r.evidence_quality for r in results) / total) if total else 0.0

    return {
        "total": total,
        "assessed": assessed,
        "passed": passed,
        "failed": failed,
        "warning": warned,
        "not_applicable": not_applicable,
        "compliance_percent": round(compliance * 100, 1),
        "evidence_quality_score": round(avg_quality, 3),
        "by_verdict": verdicts,
        "by_control_status": statuses,
    }
