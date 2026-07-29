"""Phase-2 application × common-control reusability simulation.

Fans out the existing Common Control Library across applications defined in
``config/phase2_application_portfolio.yaml``. Application identity is stamped
from configuration; technology adapters supply deterministic fixtures. No
NetBanking/MobileBanking/Payments-specific collectors.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from modules.operations.engines.common_controls_catalog import by_slug
from modules.operations.engines.common_controls_collector import (
    CollectionReceipt,
    CollectionRun,
    collect_common_control_folder,
    common_controls_root,
)
from modules.operations.engines.phase2_tech_adapters import adapt_control_evidence

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PORTFOLIO = _REPO_ROOT / "config" / "phase2_application_portfolio.yaml"

# Display alias used in product language; maps to Phase-1 catalog slug.
CONTROL_ALIASES = {
    "least-privilege": "identity-privileged-access",
    "least_privilege": "identity-privileged-access",
    "Least Privilege": "identity-privileged-access",
}


@dataclass(frozen=True)
class ApplicationProfile:
    id: str
    display_name: str
    environment: str
    cloud: str
    technologies: tuple[str, ...]
    assets: tuple[dict[str, str], ...]

    def asset_for_technology(self, technology: str) -> str:
        for row in self.assets:
            if row.get("technology") == technology:
                return str(row.get("asset_id") or f"{self.id}-{technology}")
        return f"{self.id}-{technology}"


@dataclass
class Phase2SimulationRun:
    run_id: str
    applications: list[str] = field(default_factory=list)
    controls: list[str] = field(default_factory=list)
    combinations: int = 0
    collected: int = 0
    receipts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "applications": list(self.applications),
            "controls": list(self.controls),
            "combinations": self.combinations,
            "collected": self.collected,
            "receipts": list(self.receipts),
        }


def portfolio_path() -> Path:
    override = os.environ.get("ECS_PHASE2_PORTFOLIO", "").strip()
    return Path(override) if override else DEFAULT_PORTFOLIO


def load_application_portfolio(path: Path | None = None) -> dict[str, Any]:
    target = path or portfolio_path()
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid portfolio config: {target}")
    return raw


def list_application_profiles(portfolio: dict[str, Any] | None = None) -> list[ApplicationProfile]:
    data = portfolio or load_application_portfolio()
    out: list[ApplicationProfile] = []
    for row in data.get("applications") or []:
        if not isinstance(row, dict):
            continue
        techs = tuple(str(t).strip() for t in (row.get("technologies") or []) if str(t).strip())
        assets = tuple(
            {
                "asset_id": str(a.get("asset_id") or ""),
                "technology": str(a.get("technology") or ""),
            }
            for a in (row.get("assets") or [])
            if isinstance(a, dict)
        )
        out.append(
            ApplicationProfile(
                id=str(row.get("id") or "").strip(),
                display_name=str(row.get("display_name") or row.get("id") or "").strip(),
                environment=str(row.get("environment") or "UAT").strip(),
                cloud=str(row.get("cloud") or "").strip(),
                technologies=techs,
                assets=assets,
            )
        )
    return [p for p in out if p.id and p.display_name]


def phase2_control_slugs(portfolio: dict[str, Any] | None = None) -> list[str]:
    data = portfolio or load_application_portfolio()
    slugs: list[str] = []
    for raw in data.get("phase2_controls") or []:
        slug = CONTROL_ALIASES.get(str(raw), str(raw).strip())
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def select_technology_for_control(
    app: ApplicationProfile,
    control_slug: str,
    *,
    portfolio: dict[str, Any] | None = None,
) -> str:
    techs = select_technologies_for_control(app, control_slug, portfolio=portfolio)
    if not techs:
        raise ValueError(f"No technology available for app={app.id} control={control_slug}")
    return techs[0]


def select_technologies_for_control(
    app: ApplicationProfile,
    control_slug: str,
    *,
    portfolio: dict[str, Any] | None = None,
) -> list[str]:
    """Return applicable technologies for a control from portfolio ∩ app stack."""
    data = portfolio or load_application_portfolio()
    prefs = [str(t) for t in ((data.get("control_technology_preference") or {}).get(control_slug) or [])]
    app_techs = set(app.technologies)
    matched = [t for t in prefs if t in app_techs]
    if matched:
        if bool(data.get("collect_all_matching_technologies", True)):
            return matched
        return matched[:1]
    # Fall back to first app technology only when no preference matched.
    return list(app.technologies[:1])


def _application_context(
    app: ApplicationProfile,
    *,
    technology: str,
    control_slug: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "application": app.display_name,
        "application_id": app.id,
        "environment": app.environment,
        "cloud": app.cloud,
        "asset_id": app.asset_for_technology(technology),
        "technology": technology,
        "control_slug": control_slug,
        "evidence_payload": payload,
        "phase": "phase2",
    }


def simulate_application_control_reusability(
    *,
    user: str = "scheduler",
    run_id: str = "",
    portfolio: dict[str, Any] | None = None,
    application_ids: list[str] | None = None,
) -> Phase2SimulationRun:
    """Execute configured apps × encryption controls via shared Common Controls collector."""
    data = portfolio or load_application_portfolio()
    apps = list_application_profiles(data)
    if application_ids is not None:
        want = {str(x) for x in application_ids}
        apps = [a for a in apps if a.id in want]
    controls = phase2_control_slugs(data)
    sim = Phase2SimulationRun(
        run_id=run_id or "PHASE2-REUSE",
        applications=[a.display_name for a in apps],
        controls=list(controls),
    )
    root = common_controls_root()
    for app in apps:
        for slug in controls:
            ctrl = by_slug(slug)
            folder = root / slug
            if not folder.is_dir():
                sim.receipts.append(
                    {
                        "application": app.display_name,
                        "control_slug": slug,
                        "error": f"missing CommonControls folder: {slug}",
                        "collected": False,
                    }
                )
                continue
            for technology in select_technologies_for_control(app, slug, portfolio=data):
                payload = dict(adapt_control_evidence(technology, slug))
                # Stamp application identity into the evidence body so hashing/
                # versioning remain per-app even when the same technology fixture
                # is reused (validation rules ignore these metadata fields).
                payload["application"] = app.display_name
                payload["application_id"] = app.id
                payload["environment"] = app.environment
                payload["asset_id"] = app.asset_for_technology(technology)
                ctx = _application_context(
                    app, technology=technology, control_slug=slug, payload=payload
                )
                receipt: CollectionReceipt = collect_common_control_folder(
                    folder,
                    user=user,
                    run_id=sim.run_id,
                    control_def=ctrl,
                    application_context=ctx,
                )
                sim.combinations += 1
                if receipt.collected:
                    sim.collected += 1
                sim.receipts.append(
                    {
                        "application": app.display_name,
                        "application_id": app.id,
                        "environment": app.environment,
                        "asset_id": ctx["asset_id"],
                        "technology": technology,
                        "control_slug": slug,
                        "control_id": receipt.control_id,
                        "verdict": receipt.verdict,
                        "collected": receipt.collected,
                        "evidence_key": receipt.evidence_key,
                        "error": receipt.error,
                    }
                )
    return sim


def collection_run_from_simulation(sim: Phase2SimulationRun) -> CollectionRun:
    """Shape compatible with scheduler summary merge helpers."""
    run = CollectionRun(run_id=sim.run_id)
    run.folders_discovered = sim.combinations
    run.collected = sim.collected
    return run
