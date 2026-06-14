"""Evidence Sufficiency — deterministic rules library (Phase 5.2-A).

A pure, side-effect-free scoring library. It contains NO database access, NO RAG,
NO LLM, and NO network calls. Every function takes a normalized evidence mapping
(plus a policy mapping) and returns a 0-100 sub-score together with a list of
human-readable reasons explaining how the score was derived.

The normalized evidence mapping is the union (superset) of the shapes ECS already
produces, so the same rules work for both the durable repository world and the
in-memory MVP world:

    {
      "evidence_uid": str,
      "source_system": str,
      "source_object_id": str,
      "object_type": str,            # e.g. "quality_gate", "pull_request"
      "title": str,
      "content": str,
      "owner": str,
      "url": str,
      "application": str,
      "collected_timestamp": str|datetime,   # ISO string or datetime
      "metadata": dict,
      "control_mapping": list[str],  # control IDs (alias: "controls")
      "framework_mapping": list[str],# framework refs (alias: "frameworks")
      "framework_refs": list,        # canonical (framework, ref) pairs/strings
      "lineage": list,               # any lineage records (presence = traceable)
      "review_status": str,          # evidence_reviews.status (alias: "status")
      "valid_until": str|datetime|None,
      "reviewed_at": str|datetime|None,
    }

Missing keys are tolerated; rules degrade to neutral, never raise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

# --------------------------------------------------------------------------- #
# Small, dependency-free helpers
# --------------------------------------------------------------------------- #

_TRUE_STRINGS = {"1", "true", "yes", "on", "ok", "passed", "success", "merged"}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return round(float(value), 1)


def _is_nonempty(value: Any) -> bool:
    """True when a scalar/collection carries meaningful content."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    if isinstance(value, bool):
        return value
    return True


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in _TRUE_STRINGS
    return _is_nonempty(value)


def _parse_dt(value: Any) -> datetime | None:
    """Parse an ISO-8601 string or datetime into an aware UTC datetime. None on failure."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            # Try a couple of common fallbacks (date-only, space separator).
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _controls(ev: Mapping[str, Any]) -> list[str]:
    raw = ev.get("control_mapping")
    if not raw:
        raw = ev.get("controls")
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, (list, tuple, set)):
        return [str(c) for c in raw if _is_nonempty(c)]
    return []


def _frameworks(ev: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for key in ("framework_refs", "framework_mapping", "frameworks"):
        raw = ev.get(key)
        if isinstance(raw, str) and raw.strip():
            out.append(raw.strip())
        elif isinstance(raw, (list, tuple, set)):
            for item in raw:
                if isinstance(item, (list, tuple)) and item:
                    out.append(str(item[0]))
                elif _is_nonempty(item):
                    out.append(str(item))
    return out


def _review_status(ev: Mapping[str, Any]) -> str:
    for key in ("review_status", "status"):
        val = ev.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


@dataclass
class DimensionResult:
    """Result of scoring a single dimension."""

    dimension: str
    score: float                       # 0-100
    reasons: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "reasons": list(self.reasons),
            "detail": dict(self.detail),
        }


# --------------------------------------------------------------------------- #
# SufficiencyRules — the deterministic rule catalog
# --------------------------------------------------------------------------- #

class SufficiencyRules:
    """Stateless deterministic rules. Construct with a policy mapping (the
    ``sufficiency`` block of config/sufficiency.yaml) or rely on built-in defaults.
    """

    # Defaults mirror config/sufficiency.yaml so the engine works even if the YAML
    # is absent (import-safe, test-friendly).
    DEFAULTS: dict[str, Any] = {
        "weights": {
            "completeness": 0.30, "freshness": 0.25, "traceability": 0.20,
            "coverage": 0.15, "review": 0.10,
        },
        "bands": {"ready_min": 80, "at_risk_min": 55},
        "freshness": {
            "default_max_age_days": 90,
            "max_age_days_by_type": {
                "quality_gate": 30, "security_hotspot": 30, "test_result": 14,
                "ci_build": 14, "ci_job": 14, "cloud_finding": 30,
                "pull_request": 90, "commit": 90, "branch_protection": 180,
                "release": 180, "repository": 365, "document": 365,
                "page": 365, "policy": 365,
            },
            "band_scores": {"fresh": 100, "aging": 70, "stale": 30,
                            "expired": 0, "unknown": 50},
        },
        "completeness": {
            "base_required_fields": ["title", "content", "owner", "url"],
            "require_control_mapping": True,
            "required_metadata_by_type": {
                "pull_request": ["merged", "approvals"],
                "quality_gate": ["alert_status"],
                "test_result": ["passCount", "failCount"],
                "branch_protection": ["protected"],
                "cloud_finding": ["severity", "status"],
            },
        },
        "traceability": {
            "signals": {
                "has_owner": 0.20, "has_url": 0.20, "has_control_mapping": 0.30,
                "has_lineage": 0.20, "has_source_ref": 0.10,
            },
        },
        "review": {
            "status_scores": {
                "Approved": 100, "UnderReview": 50, "Collected": 40,
                "Rejected": 0, "Expired": 0,
            },
            "unknown_status_score": 30,
        },
        "coverage": {"target_frameworks": 3, "no_mapping_score": 0},
    }

    def __init__(self, policy: Mapping[str, Any] | None = None) -> None:
        self.policy = self._merge_defaults(policy or {})

    @classmethod
    def _merge_defaults(cls, policy: Mapping[str, Any]) -> dict[str, Any]:
        """Shallow-deep merge of a partial policy over DEFAULTS (per top-level block)."""
        merged: dict[str, Any] = {}
        for key, default_val in cls.DEFAULTS.items():
            override = policy.get(key)
            if isinstance(default_val, dict) and isinstance(override, dict):
                block = dict(default_val)
                for sub_k, sub_v in override.items():
                    if isinstance(block.get(sub_k), dict) and isinstance(sub_v, dict):
                        nested = dict(block[sub_k])
                        nested.update(sub_v)
                        block[sub_k] = nested
                    elif sub_v is not None:
                        block[sub_k] = sub_v
                merged[key] = block
            elif override is not None:
                merged[key] = override
            else:
                merged[key] = default_val
        return merged

    # ---------------------------------------------------------------- weights --
    def normalized_weights(self) -> dict[str, float]:
        weights = {k: float(v) for k, v in self.policy["weights"].items()
                   if isinstance(v, (int, float)) and v >= 0}
        total = sum(weights.values())
        if total <= 0:
            # Fall back to equal weights across the five dimensions.
            keys = list(self.DEFAULTS["weights"].keys())
            return {k: 1.0 / len(keys) for k in keys}
        return {k: v / total for k, v in weights.items()}

    def band(self, score: float) -> str:
        bands = self.policy["bands"]
        if score >= float(bands.get("ready_min", 80)):
            return "Ready"
        if score >= float(bands.get("at_risk_min", 55)):
            return "At Risk"
        return "Not Ready"

    # ------------------------------------------------------------- freshness --
    def freshness_band(self, evidence: Mapping[str, Any], *, now: datetime | None = None) -> str:
        now = now or datetime.now(timezone.utc)
        valid_until = _parse_dt(evidence.get("valid_until"))
        if valid_until is not None and valid_until < now:
            return "expired"
        ref = _parse_dt(evidence.get("reviewed_at")) or _parse_dt(evidence.get("collected_timestamp"))
        if ref is None:
            return "unknown"
        age_days = max(0.0, (now - ref).total_seconds() / 86400.0)
        max_age = self._max_age_days(str(evidence.get("object_type", "")))
        if age_days > max_age:
            return "stale"
        if age_days >= 0.5 * max_age:
            return "aging"
        return "fresh"

    def _max_age_days(self, object_type: str) -> float:
        fresh = self.policy["freshness"]
        by_type = fresh.get("max_age_days_by_type", {})
        return float(by_type.get(object_type, fresh.get("default_max_age_days", 90)))

    def score_freshness(self, evidence: Mapping[str, Any], *, now: datetime | None = None) -> DimensionResult:
        band = self.freshness_band(evidence, now=now)
        band_scores = self.policy["freshness"]["band_scores"]
        score = _clamp(float(band_scores.get(band, band_scores.get("unknown", 50))))
        reasons = [f"freshness band = {band}"]
        if band == "expired":
            reasons.append(f"evidence valid_until {evidence.get('valid_until')} is in the past")
        elif band == "unknown":
            reasons.append("no usable reviewed_at/collected_timestamp -> neutral freshness")
        return DimensionResult("freshness", score, reasons, {"band": band})

    # ---------------------------------------------------------- completeness --
    def score_completeness(self, evidence: Mapping[str, Any]) -> DimensionResult:
        comp = self.policy["completeness"]
        required = list(comp.get("base_required_fields", []))
        checks: list[tuple[str, bool]] = []

        for field_name in required:
            checks.append((f"field:{field_name}", _is_nonempty(evidence.get(field_name))))

        if comp.get("require_control_mapping", True):
            checks.append(("control_mapping", len(_controls(evidence)) > 0))

        object_type = str(evidence.get("object_type", ""))
        meta_required = comp.get("required_metadata_by_type", {}).get(object_type, [])
        metadata = evidence.get("metadata") or {}
        if not isinstance(metadata, Mapping):
            metadata = {}
        for key in meta_required:
            checks.append((f"metadata:{key}", key in metadata and _is_nonempty(metadata.get(key))))

        total = len(checks) or 1
        passed = sum(1 for _, ok in checks if ok)
        score = _clamp(100.0 * passed / total)
        missing = [name for name, ok in checks if not ok]
        reasons = [f"{passed}/{total} required completeness checks passed"]
        if missing:
            reasons.append("missing: " + ", ".join(missing))
        return DimensionResult("completeness", score, reasons,
                               {"passed": passed, "total": total, "missing": missing})

    # ---------------------------------------------------------- traceability --
    def score_traceability(self, evidence: Mapping[str, Any]) -> DimensionResult:
        signals = self.policy["traceability"]["signals"]
        present: dict[str, bool] = {
            "has_owner": _is_nonempty(evidence.get("owner")),
            "has_url": _is_nonempty(evidence.get("url")),
            "has_control_mapping": len(_controls(evidence)) > 0,
            "has_lineage": _is_nonempty(evidence.get("lineage")),
            "has_source_ref": _is_nonempty(evidence.get("source_system"))
            and _is_nonempty(evidence.get("source_object_id")),
        }
        total_weight = sum(float(w) for w in signals.values()) or 1.0
        earned = sum(float(signals.get(name, 0.0)) for name, ok in present.items() if ok)
        score = _clamp(100.0 * earned / total_weight)
        missing = [name for name, ok in present.items() if not ok]
        reasons = [f"traceability signals present: {sum(present.values())}/{len(present)}"]
        if missing:
            reasons.append("missing signals: " + ", ".join(missing))
        return DimensionResult("traceability", score, reasons, {"signals": present})

    # ----------------------------------------------------------------- review --
    def score_review(self, evidence: Mapping[str, Any]) -> DimensionResult:
        review = self.policy["review"]
        status = _review_status(evidence)
        if not status:
            score = _clamp(float(review.get("unknown_status_score", 30)))
            return DimensionResult("review", score, ["no review status -> low default"],
                                   {"status": None})
        status_scores = review.get("status_scores", {})
        if status in status_scores:
            score = _clamp(float(status_scores[status]))
            reasons = [f"review status = {status}"]
        else:
            score = _clamp(float(review.get("unknown_status_score", 30)))
            reasons = [f"unrecognized review status '{status}' -> default"]
        return DimensionResult("review", score, reasons, {"status": status})

    # --------------------------------------------------------------- coverage --
    def score_coverage(self, evidence: Mapping[str, Any]) -> DimensionResult:
        cov = self.policy["coverage"]
        target = max(1, int(cov.get("target_frameworks", 3)))
        frameworks = self._distinct_frameworks(evidence)
        if not frameworks:
            score = _clamp(float(cov.get("no_mapping_score", 0)))
            return DimensionResult("coverage", score, ["no framework mappings"],
                                   {"frameworks": []})
        score = _clamp(100.0 * min(len(frameworks), target) / target)
        reasons = [f"maps to {len(frameworks)} framework(s): {', '.join(sorted(frameworks))}"]
        return DimensionResult("coverage", score, reasons, {"frameworks": sorted(frameworks)})

    @staticmethod
    def _distinct_frameworks(evidence: Mapping[str, Any]) -> set[str]:
        out: set[str] = set()
        for token in _frameworks(evidence):
            # Normalize "SOC2-CC8.1" / "ISO27001-A.14" -> base framework code.
            base = token.split("-", 1)[0].split(":", 1)[0].strip().upper()
            if base:
                out.add(base)
        return out

    # ---------------------------------------------------------- orchestration --
    def score_all(self, evidence: Mapping[str, Any], *,
                  now: datetime | None = None) -> dict[str, DimensionResult]:
        return {
            "completeness": self.score_completeness(evidence),
            "freshness": self.score_freshness(evidence, now=now),
            "traceability": self.score_traceability(evidence),
            "coverage": self.score_coverage(evidence),
            "review": self.score_review(evidence),
        }


def required_metadata_for(object_type: str, rules: SufficiencyRules | None = None) -> Sequence[str]:
    """Convenience: required metadata keys for an object_type per policy."""
    rules = rules or SufficiencyRules()
    return rules.policy["completeness"].get("required_metadata_by_type", {}).get(object_type, [])
