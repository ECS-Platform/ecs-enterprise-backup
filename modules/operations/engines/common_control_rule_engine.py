"""Generic deterministic Common-Control rule engine.

Config-driven, technology-agnostic evaluation of Common Controls from evidence
that the EXISTING predefined-query engine already produces. Nothing here knows
about a specific application, framework or bank — the rule pack
(``config/common_control_rules.yaml``) carries all of that as metadata:

    control + technology + evidence_field + operator + expected_value + aggregation

The engine:
  * loads and indexes the rule pack (by common-control slug + technology),
  * evaluates one rule against a normalized predefined-query evidence document
    (:mod:`modules.operations.engines.predefined_query_normalizer`),
  * rolls rule outcomes up into a Common Control verdict.

Verdicts (never LLM, always reproducible)::

    IMPLEMENTED | NOT_IMPLEMENTED | PARTIAL | UNKNOWN | NOT_APPLICABLE

Safety rule that outranks everything else: **missing connectivity or missing
evidence can never produce IMPLEMENTED.** An unevaluated rule is UNKNOWN, and a
control with any UNKNOWN rule can at best be PARTIAL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RULE_PACK = _REPO_ROOT / "config" / "common_control_rules.yaml"

# --------------------------------------------------------------------------- #
# Verdict vocabulary
# --------------------------------------------------------------------------- #
VERDICT_IMPLEMENTED = "IMPLEMENTED"
VERDICT_NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
VERDICT_PARTIAL = "PARTIAL"
VERDICT_UNKNOWN = "UNKNOWN"
VERDICT_NOT_APPLICABLE = "NOT_APPLICABLE"

ALL_VERDICTS: tuple[str, ...] = (
    VERDICT_IMPLEMENTED,
    VERDICT_NOT_IMPLEMENTED,
    VERDICT_PARTIAL,
    VERDICT_UNKNOWN,
    VERDICT_NOT_APPLICABLE,
)

#: Per-rule outcome statuses.
RULE_PASS = "PASS"
RULE_FAIL = "FAIL"
RULE_UNKNOWN = "UNKNOWN"

#: Reason code used when a control could not be checked because the target was
#: unreachable / the connector was unavailable at onboarding time.
REASON_CONNECTIVITY_PENDING = "CONNECTIVITY_PENDING"
REASON_EVIDENCE_MISSING = "EVIDENCE_MISSING"
REASON_FIELD_MISSING = "FIELD_MISSING"
REASON_NO_RULES = "NO_RULES_CONFIGURED"

# --------------------------------------------------------------------------- #
# Operators
# --------------------------------------------------------------------------- #
#: Minimum operator set required by the control specification, plus
#: ``not_contains`` which weak-protocol / default-credential rules need to be
#: expressible at all. Adding an operator is a one-line change here.
OPERATORS: tuple[str, ...] = (
    "equals",
    "not_equals",
    "exists",
    "gte",
    "lte",
    "contains",
    "not_contains",
)

#: Aggregations applied when ``evidence_field`` resolves to a *column* over many
#: rows (e.g. one row per tablespace / per DB user / per asset row).
AGGREGATIONS: tuple[str, ...] = ("all", "any", "none", "first")

_MISSING = object()


def _as_float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _norm_scalar(value: Any) -> str:
    return str(value).strip().lower()


def apply_operator(operator: str, actual: Any, expected: Any) -> bool:
    """Deterministically apply one operator. Unknown operators raise."""
    op = (operator or "").strip().lower()
    if op not in OPERATORS:
        raise ValueError(f"Unsupported operator: {operator!r} (supported: {', '.join(OPERATORS)})")

    if op == "exists":
        return actual is not None and _norm_scalar(actual) != ""

    if op in ("gte", "lte"):
        a, e = _as_float(actual), _as_float(expected)
        if a is None or e is None:
            return False
        return a >= e if op == "gte" else a <= e

    if op in ("contains", "not_contains"):
        hay = _norm_scalar(actual)
        needles = expected if isinstance(expected, (list, tuple)) else [expected]
        hit = any(_norm_scalar(n) in hay for n in needles)
        return hit if op == "contains" else not hit

    # equals / not_equals — numeric comparison when both sides are numeric,
    # case-insensitive string comparison otherwise. A list expectation means
    # "is one of".
    candidates = expected if isinstance(expected, (list, tuple)) else [expected]
    matched = False
    for cand in candidates:
        a, e = _as_float(actual), _as_float(cand)
        if a is not None and e is not None:
            matched = a == e
        else:
            matched = _norm_scalar(actual) == _norm_scalar(cand)
        if matched:
            break
    return matched if op == "equals" else not matched


# --------------------------------------------------------------------------- #
# Rule model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ControlRule:
    """One config-driven rule. All fields come from the YAML rule pack."""

    rule_id: str
    control: str                 # common-control slug (framework independent)
    technology: str              # canonical predefined-query technology label
    predefined_query_id: str     # existing PQ that supplies the evidence
    evidence_field: str
    operator: str = "equals"
    expected_value: Any = None
    aggregation: str = "all"
    severity: str = "medium"
    description: str = ""
    parse: str = ""              # optional normalizer hint: auto | text | rows

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "control": self.control,
            "technology": self.technology,
            "predefined_query_id": self.predefined_query_id,
            "evidence_field": self.evidence_field,
            "operator": self.operator,
            "expected_value": self.expected_value,
            "aggregation": self.aggregation,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class RuleOutcome:
    """Result of evaluating one rule against one normalized evidence document."""

    rule_id: str
    control: str
    technology: str
    predefined_query_id: str
    evidence_field: str
    operator: str
    expected_value: Any
    aggregation: str
    status: str = RULE_UNKNOWN          # PASS | FAIL | UNKNOWN
    actual_value: Any = None
    reason: str = ""
    reason_code: str = ""
    severity: str = "medium"
    evidence_id: str = ""
    evidence_source: str = ""
    rows_evaluated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "control": self.control,
            "technology": self.technology,
            "predefined_query_id": self.predefined_query_id,
            "evidence_field": self.evidence_field,
            "operator": self.operator,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "aggregation": self.aggregation,
            "status": self.status,
            "reason": self.reason,
            "reason_code": self.reason_code,
            "severity": self.severity,
            "evidence_id": self.evidence_id,
            "evidence_source": self.evidence_source,
            "rows_evaluated": self.rows_evaluated,
        }


@dataclass(frozen=True)
class ControlMeta:
    """Display name + FCM domain keywords for a control slug (config-driven).

    Slugs already present in the frozen Phase-1 CommonControls catalogue
    (:mod:`modules.operations.engines.common_controls_catalog`) don't need an
    entry here — :func:`control_metadata` falls back to that catalogue first.
    This block only covers slugs the rule pack introduces on its own (e.g.
    ``password-policy``), so FCM domain keywords are never hardcoded in code.
    """

    slug: str
    control_id: str
    name: str
    match_domains: tuple[str, ...] = ()


@dataclass
class RulePack:
    version: str = ""
    description: str = ""
    rules: tuple[ControlRule, ...] = ()
    index: dict[tuple[str, str], tuple[ControlRule, ...]] = field(default_factory=dict)
    control_meta: dict[str, ControlMeta] = field(default_factory=dict)

    def controls(self) -> list[str]:
        return sorted({r.control for r in self.rules})

    def technologies(self) -> list[str]:
        return sorted({r.technology for r in self.rules})

    def technologies_for_control(self, control: str) -> list[str]:
        key = _key(control)
        return sorted({r.technology for r in self.rules if _key(r.control) == key})

    def controls_for_technology(self, technology: str) -> list[str]:
        key = _key(technology)
        return sorted({r.control for r in self.rules if _key(r.technology) == key})

    def rules_for(self, control: str, technology: str) -> list[ControlRule]:
        return list(self.index.get((_key(control), _key(technology)), ()))

    def predefined_query_ids(self, control: str, technology: str) -> list[str]:
        seen: list[str] = []
        for rule in self.rules_for(control, technology):
            if rule.predefined_query_id and rule.predefined_query_id not in seen:
                seen.append(rule.predefined_query_id)
        return seen


def _key(value: str) -> str:
    return (value or "").strip().lower()


# --------------------------------------------------------------------------- #
# Rule pack loading
# --------------------------------------------------------------------------- #
def rule_pack_path() -> Path:
    override = os.environ.get("ECS_COMMON_CONTROL_RULES", "").strip()
    return Path(override) if override else DEFAULT_RULE_PACK


def parse_rule_pack(raw: dict[str, Any]) -> RulePack:
    """Build a :class:`RulePack` from already-parsed YAML/JSON (no file IO)."""
    if not isinstance(raw, dict):
        raise ValueError("Rule pack must be a mapping")
    defaults = dict(raw.get("defaults") or {})
    default_operator = str(defaults.get("operator") or "equals")
    default_aggregation = str(defaults.get("aggregation") or "all")
    default_severity = str(defaults.get("severity") or "medium")

    rules: list[ControlRule] = []
    for idx, row in enumerate(raw.get("rules") or []):
        if not isinstance(row, dict):
            continue
        control = str(row.get("control") or "").strip()
        technology = str(row.get("technology") or "").strip()
        evidence_field = str(row.get("evidence_field") or "").strip()
        if not (control and technology and evidence_field):
            raise ValueError(
                f"Rule #{idx} is incomplete — control, technology and evidence_field are required"
            )
        operator = str(row.get("operator") or default_operator).strip().lower()
        if operator not in OPERATORS:
            raise ValueError(f"Rule {row.get('id') or idx}: unsupported operator {operator!r}")
        aggregation = str(row.get("aggregation") or default_aggregation).strip().lower()
        if aggregation not in AGGREGATIONS:
            raise ValueError(f"Rule {row.get('id') or idx}: unsupported aggregation {aggregation!r}")
        rules.append(
            ControlRule(
                rule_id=str(row.get("id") or f"RULE-{idx:04d}"),
                control=control,
                technology=technology,
                predefined_query_id=str(row.get("predefined_query_id") or "").strip(),
                evidence_field=evidence_field,
                operator=operator,
                expected_value=row.get("expected_value"),
                aggregation=aggregation,
                severity=str(row.get("severity") or default_severity),
                description=str(row.get("description") or ""),
                parse=str(row.get("parse") or "").strip().lower(),
            )
        )

    index: dict[tuple[str, str], tuple[ControlRule, ...]] = {}
    for rule in rules:
        key = (_key(rule.control), _key(rule.technology))
        index[key] = index.get(key, ()) + (rule,)

    control_meta: dict[str, ControlMeta] = {}
    for slug, row in (raw.get("controls") or {}).items():
        if not isinstance(row, dict):
            continue
        control_meta[_key(slug)] = ControlMeta(
            slug=str(slug),
            control_id=str(row.get("control_id") or f"CC-{str(slug).upper().replace('-', '_')}"),
            name=str(row.get("name") or slug),
            match_domains=tuple(str(d) for d in (row.get("match_domains") or [])),
        )

    return RulePack(
        version=str(raw.get("version") or ""),
        description=str(raw.get("description") or ""),
        rules=tuple(rules),
        index=index,
        control_meta=control_meta,
    )


def control_metadata(control: str, pack: "RulePack | None" = None) -> ControlMeta:
    """Display name + FCM match domains for a control slug.

    Prefers the frozen Phase-1 CommonControls catalogue (so its FCM domain
    mapping is reused verbatim); falls back to the rule pack's own
    ``controls:`` block for slugs the catalogue doesn't define; falls back to
    a bare slug-derived label as a last resort so callers never crash on an
    unmapped control.
    """
    from modules.operations.engines.common_controls_catalog import by_slug as _cc_by_slug

    legacy = _cc_by_slug(control)
    if legacy is not None:
        return ControlMeta(
            slug=legacy.slug,
            control_id=legacy.control_id,
            name=legacy.name,
            match_domains=legacy.match_domains,
        )
    rp = pack or load_rule_pack()
    meta = rp.control_meta.get(_key(control))
    if meta is not None:
        return meta
    slug = (control or "").strip()
    return ControlMeta(slug=slug, control_id=f"CC-{slug.upper().replace('-', '_')}", name=slug)


@lru_cache(maxsize=4)
def _load_rule_pack_cached(path_str: str, mtime: float) -> RulePack:
    raw = yaml.safe_load(Path(path_str).read_text(encoding="utf-8")) or {}
    return parse_rule_pack(raw)


def load_rule_pack(path: Path | None = None) -> RulePack:
    """Load (and memoize by path+mtime) the configured rule pack."""
    target = path or rule_pack_path()
    try:
        mtime = target.stat().st_mtime
    except OSError as exc:  # pragma: no cover - surfaced to caller as-is
        raise FileNotFoundError(f"Common-control rule pack not found: {target}") from exc
    return _load_rule_pack_cached(str(target), mtime)


def reset_cache() -> None:
    """Drop the memoized rule pack (use after editing the YAML in-process)."""
    _load_rule_pack_cached.cache_clear()


# --------------------------------------------------------------------------- #
# Rule evaluation
# --------------------------------------------------------------------------- #
def _resolve_field(evidence: Any, field_name: str) -> tuple[str, Any]:
    """Resolve ``field_name`` against a normalized evidence document.

    Returns ``(kind, value)`` where kind is ``scalar``, ``rows`` or ``missing``.
    """
    fields = getattr(evidence, "fields", None) or {}
    key = _key(field_name)
    for name, value in fields.items():
        if _key(name) == key:
            return "scalar", value
    columns = [c for c in (getattr(evidence, "columns", None) or []) if _key(c) == key]
    if columns:
        rows = getattr(evidence, "rows", None) or []
        column = columns[0]
        return "rows", [row.get(column) for row in rows]
    return "missing", _MISSING


def evaluate_rule(rule: ControlRule, evidence: Any) -> RuleOutcome:
    """Evaluate one rule against one normalized evidence document.

    ``evidence`` is a
    :class:`~modules.operations.engines.predefined_query_normalizer.NormalizedEvidence`
    (duck-typed here so the engine stays import-light and unit-testable).
    """
    outcome = RuleOutcome(
        rule_id=rule.rule_id,
        control=rule.control,
        technology=rule.technology,
        predefined_query_id=rule.predefined_query_id,
        evidence_field=rule.evidence_field,
        operator=rule.operator,
        expected_value=rule.expected_value,
        aggregation=rule.aggregation,
        severity=rule.severity,
        evidence_id=str(getattr(evidence, "evidence_id", "") or ""),
        evidence_source=str(getattr(evidence, "source", "") or ""),
    )

    if evidence is None:
        outcome.status = RULE_UNKNOWN
        outcome.reason_code = REASON_EVIDENCE_MISSING
        outcome.reason = (
            f"No evidence collected for {rule.predefined_query_id or rule.technology} — "
            "control cannot be asserted."
        )
        return outcome

    if not getattr(evidence, "ok", False):
        outcome.status = RULE_UNKNOWN
        outcome.reason_code = str(getattr(evidence, "reason_code", "") or REASON_EVIDENCE_MISSING)
        outcome.reason = (
            str(getattr(evidence, "error", "") or "Evidence collection did not succeed")
            + f" (predefined query {rule.predefined_query_id or 'n/a'})"
        )
        return outcome

    kind, value = _resolve_field(evidence, rule.evidence_field)
    if kind == "missing":
        outcome.status = RULE_UNKNOWN
        outcome.reason_code = REASON_FIELD_MISSING
        outcome.reason = (
            f"Field '{rule.evidence_field}' not present in evidence from "
            f"{rule.predefined_query_id or rule.technology}."
        )
        return outcome

    if kind == "scalar":
        outcome.actual_value = value
        outcome.rows_evaluated = 1
        passed = apply_operator(rule.operator, value, rule.expected_value)
    else:
        values = list(value)
        outcome.rows_evaluated = len(values)
        if not values:
            # No rows at all: 'none' is vacuously satisfied, everything else is
            # unknown — an empty result set is not proof of implementation.
            if rule.aggregation == "none":
                outcome.actual_value = []
                outcome.status = RULE_PASS
                outcome.reason = (
                    f"No rows returned by {rule.predefined_query_id or rule.technology}; "
                    "aggregation 'none' satisfied."
                )
                return outcome
            outcome.status = RULE_UNKNOWN
            outcome.reason_code = REASON_EVIDENCE_MISSING
            outcome.reason = (
                f"{rule.predefined_query_id or rule.technology} returned no rows for "
                f"'{rule.evidence_field}' — nothing to evaluate."
            )
            return outcome

        matches = [apply_operator(rule.operator, v, rule.expected_value) for v in values]
        if rule.aggregation == "all":
            passed = all(matches)
            outcome.actual_value = [v for v, m in zip(values, matches) if not m][:5] or values[:5]
        elif rule.aggregation == "any":
            passed = any(matches)
            outcome.actual_value = values[:5]
        elif rule.aggregation == "none":
            passed = not any(matches)
            outcome.actual_value = [v for v, m in zip(values, matches) if m][:5]
        else:  # first
            passed = matches[0]
            outcome.actual_value = values[0]

    outcome.status = RULE_PASS if passed else RULE_FAIL
    outcome.reason = _explain(rule, outcome, passed)
    return outcome


def _explain(rule: ControlRule, outcome: RuleOutcome, passed: bool) -> str:
    label = rule.description or f"{rule.control} / {rule.technology}"
    expectation = f"{rule.operator} {rule.expected_value!r}"
    if rule.operator == "exists":
        expectation = "must be present"
    scope = (
        "" if outcome.rows_evaluated <= 1
        else f" over {outcome.rows_evaluated} row(s) [{rule.aggregation}]"
    )
    verdict = "satisfied" if passed else "not satisfied"
    return (
        f"{label}: '{rule.evidence_field}' {expectation}{scope} — {verdict} "
        f"(actual={outcome.actual_value!r}, source={rule.predefined_query_id or 'n/a'})"
    )


# --------------------------------------------------------------------------- #
# Verdict aggregation
# --------------------------------------------------------------------------- #
def verdict_from_rule_outcomes(outcomes: list[RuleOutcome]) -> str:
    """Roll a set of rule outcomes up into a Common Control verdict.

    Missing evidence never yields IMPLEMENTED: a control with any UNKNOWN rule
    is capped at PARTIAL (when something else passed) or UNKNOWN.
    """
    if not outcomes:
        return VERDICT_NOT_APPLICABLE
    passed = sum(1 for o in outcomes if o.status == RULE_PASS)
    failed = sum(1 for o in outcomes if o.status == RULE_FAIL)
    unknown = sum(1 for o in outcomes if o.status == RULE_UNKNOWN)

    if unknown and not passed and not failed:
        return VERDICT_UNKNOWN
    if passed and not failed and not unknown:
        return VERDICT_IMPLEMENTED
    if failed and not passed:
        # A definite failure is decisive even when other rules are unknown.
        return VERDICT_NOT_IMPLEMENTED
    return VERDICT_PARTIAL


def aggregate_verdicts(verdicts: list[str]) -> str:
    """Roll verdicts up across assets / technologies / controls.

    NOT_APPLICABLE is ignored whenever anything else was actually evaluated.
    """
    values = [v for v in verdicts if v]
    if not values:
        return VERDICT_NOT_APPLICABLE
    considered = [v for v in values if v != VERDICT_NOT_APPLICABLE]
    if not considered:
        return VERDICT_NOT_APPLICABLE
    if all(v == VERDICT_IMPLEMENTED for v in considered):
        return VERDICT_IMPLEMENTED
    if all(v == VERDICT_UNKNOWN for v in considered):
        return VERDICT_UNKNOWN
    if all(v == VERDICT_NOT_IMPLEMENTED for v in considered):
        return VERDICT_NOT_IMPLEMENTED
    if VERDICT_IMPLEMENTED in considered or VERDICT_PARTIAL in considered:
        return VERDICT_PARTIAL
    # Only NOT_IMPLEMENTED + UNKNOWN remain.
    return VERDICT_NOT_IMPLEMENTED


def is_applicable(control: str, technology: str, pack: RulePack | None = None) -> bool:
    """A control applies to a technology only if the rule pack configures it."""
    rp = pack or load_rule_pack()
    return bool(rp.rules_for(control, technology))
