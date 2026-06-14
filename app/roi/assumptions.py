"""ROI assumptions — configuration loading & accessors.

Loads the 'roi' block from config/roi.yaml (env-overridable), validates/coerces it,
and exposes a single ``Assumptions`` object. Fail-safe: if config is missing or
malformed, sensible documented defaults are used so the engine never crashes.

NO hardcoded business numbers live in the UI — they all originate here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

_TRUTHY = {"1", "true", "yes", "on"}

# Documented fallback defaults (mirror config/roi.yaml).
_DEFAULTS: dict[str, Any] = {
    "currency": {"symbol": "₹", "code": "INR", "lakh": 100_000, "crore": 10_000_000},
    "assumptions": {
        "applications_in_bank": 905,
        "vapt_applications": 600,
        "observations_per_application": 2.5,
        "emails_per_observation": 7,
        "hours_per_observation": 8,
        "hours_per_email": 0.25,
        "hours_per_audit": 160,
        "hours_per_framework_onboarding": 80,
        "cost_per_hour": 1500,
        "working_hours_per_fte_year": 1800,
        "baseline_savings_per_25_apps_cr": 4.5,
    },
    "efficiency": {
        "email_reduction_pct": 0.85,
        "observation_effort_reduction_pct": 0.6,
        "observation_prevention_pct": 0.3,
        "audit_effort_reduction_pct": 0.55,
        "framework_onboarding_reduction_pct": 0.7,
        "evidence_reuse_factor": 4,
        "reuse_hours_saved_each": 1.5,
        "closure_acceleration_pct": 0.65,
        "cost_per_app_per_year": 60_000,
    },
    "risk": {"per_app_reduction_pct": 0.12, "max_reduction_pct": 78},
    "onboarding": {
        "apps_per_year": 100,
        "storyboard_apps": [25, 100, 200],
        "projection_apps": [25, 100, 200, 400, 600],
        "projection_years": [1, 2, 3, 4, 5],
    },
    "frameworks": [
        {"name": "VAPT", "apps_covered": 600, "weight": 1.4, "reuse_factor": 5},
        {"name": "RBI", "coverage_pct": 0.9, "weight": 1.2, "reuse_factor": 4},
        {"name": "ISO27001", "coverage_pct": 0.7, "weight": 1.0, "reuse_factor": 4},
        {"name": "PCI-DSS", "coverage_pct": 0.4, "weight": 1.1, "reuse_factor": 3},
        {"name": "SWIFT", "coverage_pct": 0.25, "weight": 1.0, "reuse_factor": 3},
        {"name": "AI Governance", "coverage_pct": 0.15, "weight": 0.8, "reuse_factor": 2},
    ],
}


def roi_enabled() -> bool:
    """ROI Center master flag (env wins over config). Default OFF."""
    env = os.environ.get("ROI_CENTER_ENABLED")
    if env is not None and env != "":
        return env.strip().lower() in _TRUTHY
    try:
        block = _load_block()
        val = block.get("enabled", False)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in _TRUTHY
    except Exception:  # noqa: BLE001
        pass
    return False


def _load_block() -> dict[str, Any]:
    try:
        from ecs_platform.config.loader import load_config
        cfg = load_config("roi") or {}
        block = cfg.get("roi", cfg)
        return block if isinstance(block, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _num(value: Any, default: float) -> float:
    try:
        if isinstance(value, bool):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _merge(defaults: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in defaults.items():
        if isinstance(v, dict):
            ov = override.get(k) if isinstance(override, dict) else None
            out[k] = _merge(v, ov if isinstance(ov, dict) else {})
        else:
            out[k] = override.get(k, v) if isinstance(override, dict) else v
    # Preserve override-only keys (e.g. extra framework fields).
    if isinstance(override, dict):
        for k, v in override.items():
            if k not in out:
                out[k] = v
    return out


@dataclass
class Assumptions:
    raw: dict[str, Any] = field(default_factory=dict)

    # currency
    symbol: str = "₹"
    code: str = "INR"
    lakh: int = 100_000
    crore: int = 10_000_000

    # baseline
    applications_in_bank: int = 905
    vapt_applications: int = 600
    observations_per_application: float = 2.5
    emails_per_observation: float = 7
    hours_per_observation: float = 8
    hours_per_email: float = 0.25
    hours_per_audit: float = 160
    hours_per_framework_onboarding: float = 80
    cost_per_hour: float = 1500
    working_hours_per_fte_year: float = 1800
    baseline_savings_per_25_apps_cr: float = 4.5

    # efficiency
    email_reduction_pct: float = 0.85
    observation_effort_reduction_pct: float = 0.6
    observation_prevention_pct: float = 0.3
    audit_effort_reduction_pct: float = 0.55
    framework_onboarding_reduction_pct: float = 0.7
    evidence_reuse_factor: float = 4
    reuse_hours_saved_each: float = 1.5
    closure_acceleration_pct: float = 0.65
    cost_per_app_per_year: float = 60_000

    # risk
    per_app_reduction_pct: float = 0.12
    max_reduction_pct: float = 78

    # onboarding
    apps_per_year: int = 100
    storyboard_apps: list = field(default_factory=lambda: [25, 100, 200])
    projection_apps: list = field(default_factory=lambda: [25, 100, 200, 400, 600])
    projection_years: list = field(default_factory=lambda: [1, 2, 3, 4, 5])

    frameworks: list = field(default_factory=list)

    # scenario context (set by for_scenario; defaults represent the baseline)
    active_scenario: str = "expected"
    scenario_label: str = "Expected"
    adoption_pct: float = 1.0

    @classmethod
    def load(cls) -> "Assumptions":
        merged = _merge(_DEFAULTS, _load_block())
        cur = merged["currency"]; a = merged["assumptions"]
        e = merged["efficiency"]; r = merged["risk"]; o = merged["onboarding"]
        inst = cls(
            raw=merged,
            symbol=str(cur.get("symbol", "₹")), code=str(cur.get("code", "INR")),
            lakh=int(_num(cur.get("lakh"), 100_000)),
            crore=int(_num(cur.get("crore"), 10_000_000)),
            applications_in_bank=int(_num(a.get("applications_in_bank"), 905)),
            vapt_applications=int(_num(a.get("vapt_applications"), 600)),
            observations_per_application=_num(a.get("observations_per_application"), 2.5),
            emails_per_observation=_num(a.get("emails_per_observation"), 7),
            hours_per_observation=_num(a.get("hours_per_observation"), 8),
            hours_per_email=_num(a.get("hours_per_email"), 0.25),
            hours_per_audit=_num(a.get("hours_per_audit"), 160),
            hours_per_framework_onboarding=_num(a.get("hours_per_framework_onboarding"), 80),
            cost_per_hour=_num(a.get("cost_per_hour"), 1500),
            working_hours_per_fte_year=_num(a.get("working_hours_per_fte_year"), 1800),
            baseline_savings_per_25_apps_cr=_num(a.get("baseline_savings_per_25_apps_cr"), 4.5),
            email_reduction_pct=_num(e.get("email_reduction_pct"), 0.85),
            observation_effort_reduction_pct=_num(e.get("observation_effort_reduction_pct"), 0.6),
            observation_prevention_pct=_num(e.get("observation_prevention_pct"), 0.3),
            audit_effort_reduction_pct=_num(e.get("audit_effort_reduction_pct"), 0.55),
            framework_onboarding_reduction_pct=_num(e.get("framework_onboarding_reduction_pct"), 0.7),
            evidence_reuse_factor=_num(e.get("evidence_reuse_factor"), 4),
            reuse_hours_saved_each=_num(e.get("reuse_hours_saved_each"), 1.5),
            closure_acceleration_pct=_num(e.get("closure_acceleration_pct"), 0.65),
            cost_per_app_per_year=_num(e.get("cost_per_app_per_year"), 60_000),
            per_app_reduction_pct=_num(r.get("per_app_reduction_pct"), 0.12),
            max_reduction_pct=_num(r.get("max_reduction_pct"), 78),
            apps_per_year=int(_num(o.get("apps_per_year"), 100)),
            storyboard_apps=list(o.get("storyboard_apps") or [25, 100, 200]),
            projection_apps=list(o.get("projection_apps") or [25, 100, 200, 400, 600]),
            projection_years=list(o.get("projection_years") or [1, 2, 3, 4, 5]),
            frameworks=list(merged.get("frameworks") or []),
        )
        return inst

    def baseline_cost_per_app(self) -> float:
        """Derive ₹/app from the ₹4.5 Cr-per-25-apps anchor."""
        per_25 = self.baseline_savings_per_25_apps_cr * self.crore
        return per_25 / 25.0 if 25 else 0.0

    # -- scenario support (additive) ---------------------------------------- #
    def scenario_names(self) -> list[str]:
        scn = self.raw.get("scenarios", {}) if isinstance(self.raw, dict) else {}
        return list(scn.keys()) or ["conservative", "expected", "aggressive"]

    def default_scenario(self) -> str:
        name = (self.raw.get("default_scenario") if isinstance(self.raw, dict) else None)
        names = self.scenario_names()
        return name if name in names else ("expected" if "expected" in names else names[0])

    def for_scenario(self, scenario: str | None) -> "Assumptions":
        """Return a NEW Assumptions with the named scenario's overrides applied.

        Non-destructive: the receiver is unchanged. Unknown scenario -> default.
        Never raises.
        """
        try:
            scn_all = self.raw.get("scenarios", {}) if isinstance(self.raw, dict) else {}
            name = scenario if scenario in scn_all else self.default_scenario()
            override = scn_all.get(name, {}) if isinstance(scn_all, dict) else {}
            if not isinstance(override, dict):
                override = {}

            import copy
            inst = copy.deepcopy(self)
            inst.active_scenario = name
            inst.scenario_label = str(override.get("label", name.title()))

            # Adoption + target applications drive the "in scope" universe.
            adoption = _num(override.get("adoption_pct"), 1.0)
            target = override.get("target_applications")
            if target is not None:
                base_apps = int(_num(target, self.applications_in_bank))
            else:
                base_apps = self.applications_in_bank
            inst.applications_in_bank = max(0, int(round(base_apps * adoption)))
            inst.adoption_pct = adoption

            # Scalar overrides (only when present).
            for attr in ("observations_per_application", "emails_per_observation",
                         "email_reduction_pct", "evidence_reuse_factor",
                         "observation_prevention_pct", "closure_acceleration_pct",
                         "audit_effort_reduction_pct",
                         "framework_onboarding_reduction_pct"):
                if attr in override:
                    setattr(inst, attr, _num(override.get(attr), getattr(self, attr)))

            # Framework subset for the scenario (filter the configured list).
            fw_names = override.get("frameworks")
            if isinstance(fw_names, list) and fw_names:
                wanted = {str(x).lower() for x in fw_names}
                filtered = [f for f in self.frameworks
                            if str(f.get("name", "")).lower() in wanted]
                inst.frameworks = filtered or self.frameworks
            return inst
        except Exception:  # noqa: BLE001
            return self
