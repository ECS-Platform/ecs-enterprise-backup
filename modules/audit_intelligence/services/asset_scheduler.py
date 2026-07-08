"""UAT asset-driven scheduler & evidence routing (audit-intelligence service).

This is the missing **asset-driven scheduler layer**. It reads a UAT/local asset
configuration file, classifies each asset's technology, maps it to an evidence
scope + a *collector route* (an existing enterprise connector or the baseline
predefined-query collector), and produces a bounded **evidence collection plan**.
A **dry-run** runner turns that plan into a deterministic, side-effect-free report
suitable for CI, demos, and pre-UAT verification.

Design principles
-----------------
* **Reuse, don't reinvent.** Classification reuses
  :mod:`modules.audit_intelligence.engines.technology_fingerprint`; asset
  normalization reuses :func:`asset_discovery.discover_from_manual`; control
  scoping reuses :func:`evidence_orchestrator.resolve_scope`; connector routing
  reuses the :mod:`modules.operations.integrations` registry. No connector code is
  duplicated or modified here.
* **Offline & safe by default.** Nothing here opens a socket. The dry-run planner
  never executes a query or calls a connector — it only *plans* and reports what
  *would* run, plus config-only connector readiness (SET/MISSING). Live execution
  is explicitly opt-in and delegated to the existing evidence service.
* **No secrets, no bank values.** Only non-secret asset metadata is handled;
  connector credentials stay in env/secret store and are surfaced masked only.

Public surface
--------------
* :func:`load_asset_config` / :func:`load_assets` — YAML/dict -> normalized assets.
* :func:`classify_asset` — Asset -> :class:`AssetClassification` (tech + route).
* :func:`plan_evidence` — assets -> :class:`EvidencePlan` (bounded, deterministic).
* :func:`dry_run` — assets/config -> a JSON-safe dry-run report (no side effects).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from modules.audit_intelligence.engines import asset_discovery
from modules.audit_intelligence.engines import evidence_orchestrator as orch
from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.models import Asset

_REPO_ROOT = Path(__file__).resolve().parents[3]

#: Bound the plan so a huge/hostile config can never explode the run.
_MAX_ASSETS = 1000
_MAX_CONTROLS_PER_ASSET = 500

# --------------------------------------------------------------------------- #
# Collector routes
# --------------------------------------------------------------------------- #
#: Route kinds an asset can be dispatched to.
ROUTE_BASELINE = "baseline_collector"      # predefined-query engine for the tech
ROUTE_CONNECTOR = "enterprise_connector"    # a modules.operations.integrations adapter
ROUTE_UNSUPPORTED = "unsupported"           # no controls + no connector -> manual/fallback

#: Explicit asset-type / technology -> enterprise connector adapter module.
#: Keys are matched case-insensitively against the asset's declared ``asset_type``
#: (preferred) or its classified technology. Values are adapter module names in
#: :mod:`modules.operations.integrations` (never re-implemented here).
_CONNECTOR_ROUTES: dict[str, str] = {
    # ITSM / CMDB
    "servicenow": "servicenow_cmdb",
    "servicenow_cmdb": "servicenow_cmdb",
    "cmdb": "servicenow_cmdb",
    "archer": "archer",
    # Microsoft Graph family
    "sharepoint": "sharepoint_graph",
    "sharepoint_graph": "sharepoint_graph",
    "graph": "sharepoint_graph",
    "teams": "teams_graph",
    "teams_graph": "teams_graph",
    "outlook": "outlook_graph",
    "outlook_graph": "outlook_graph",
    "exchange": "outlook_graph",
    # Collaboration / ALM
    "jira": "jira",
    "confluence": "confluence",
    # CI/CD + SCM (adapters wrap the ecs_platform connector clients)
    "github": "github",
    "jenkins": "jenkins",
    "azure_devops": "azure_devops",
    "azuredevops": "azure_devops",
    "azure devops": "azure_devops",
    # AppSec
    "sonarqube": "sonarqube",
    "checkmarx": "checkmarx",
    "prisma": "prisma_cloud",
    "prisma_cloud": "prisma_cloud",
    # FIM
    "tripwire": "tripwire",
    # Cloud posture
    "aws": "aws_connector",
    "gcp": "gcp_connector",
    "azure": "azure_connector",
    # Vulnerability scanners
    "nessus": "nessus",
    "tenable": "nessus",
    "qualys": "qualys",
}


def connector_routes() -> dict[str, str]:
    """The asset-type/technology -> connector adapter routing table (copy)."""
    return dict(_CONNECTOR_ROUTES)


# --------------------------------------------------------------------------- #
# Classification model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AssetClassification:
    """The routing decision for a single asset (deterministic, offline)."""

    asset_id: str
    hostname: str = ""
    environment: str = ""
    technology: str = ""
    confidence: float = 0.0
    route: str = ROUTE_UNSUPPORTED
    connector: str = ""                       # adapter module name when route=connector
    scope_kind: str = ""                      # technology | connector | unsupported
    scope_value: str = ""
    control_ids: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "hostname": self.hostname,
            "environment": self.environment,
            "technology": self.technology,
            "confidence": round(self.confidence, 3),
            "route": self.route,
            "connector": self.connector,
            "scope_kind": self.scope_kind,
            "scope_value": self.scope_value,
            "control_ids": list(self.control_ids),
            "control_count": len(self.control_ids),
            "frameworks": list(self.frameworks),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class PlannedJob:
    """One planned evidence-collection job for a classified asset."""

    asset_id: str
    technology: str
    route: str
    connector: str
    scope_kind: str
    scope_value: str
    control_ids: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "technology": self.technology,
            "route": self.route,
            "connector": self.connector,
            "scope_kind": self.scope_kind,
            "scope_value": self.scope_value,
            "control_ids": list(self.control_ids),
            "control_count": len(self.control_ids),
            "frameworks": list(self.frameworks),
        }


@dataclass
class EvidencePlan:
    """A bounded, deterministic evidence plan over a set of classified assets."""

    jobs: list[PlannedJob] = field(default_factory=list)
    unsupported: list[AssetClassification] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        by_route: dict[str, int] = {}
        by_tech: dict[str, int] = {}
        total_controls = 0
        for job in self.jobs:
            by_route[job.route] = by_route.get(job.route, 0) + 1
            by_tech[job.technology or "Unknown"] = by_tech.get(job.technology or "Unknown", 0) + 1
            total_controls += len(job.control_ids)
        return {
            "jobs": [j.to_dict() for j in self.jobs],
            "unsupported": [u.to_dict() for u in self.unsupported],
            "summary": {
                "planned_jobs": len(self.jobs),
                "unsupported_assets": len(self.unsupported),
                "total_planned_controls": total_controls,
                "by_route": by_route,
                "by_technology": by_tech,
            },
        }


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #
def _default_config_path() -> Path:
    return _REPO_ROOT / "config" / "uat_assets.local.yaml"


def load_asset_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load a UAT asset YAML config into a plain dict. Never raises.

    Returns ``{}`` if the file is missing/unreadable/malformed so callers degrade
    gracefully (an empty plan rather than a crash).
    """
    cfg_path = Path(path) if path else _default_config_path()
    if not cfg_path.is_file():
        return {}
    try:
        import yaml

        with cfg_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001 - malformed/missing -> empty config
        return {}
    return data if isinstance(data, dict) else {}


def _expand(value: Any) -> Any:
    """Expand ``${VAR}`` / ``${VAR:-default}`` in strings (env-driven, no secrets in file)."""
    if not isinstance(value, str) or "${" not in value:
        return value
    out = value
    # Minimal, dependency-free expansion of ${VAR} and ${VAR:-default}.
    import re

    def repl(m: "re.Match[str]") -> str:
        token = m.group(1)
        if ":-" in token:
            name, default = token.split(":-", 1)
        else:
            name, default = token, ""
        return os.environ.get(name.strip(), default)

    return re.sub(r"\$\{([^}]+)\}", repl, out)


def _asset_records_from_config(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the raw asset dicts from a config, expanding placeholders.

    Accepts either ``{"assets": [...]}`` or a bare top-level list under common
    keys. Each record keeps an optional ``asset_type`` used for connector routing.
    """
    raw = cfg.get("assets")
    if raw is None:
        raw = cfg.get("uat_assets") or cfg.get("inventory") or []
    records: list[dict[str, Any]] = []
    for rec in list(raw or [])[:_MAX_ASSETS]:
        if not isinstance(rec, dict):
            continue
        expanded = {k: _expand(v) for k, v in rec.items()}
        records.append(expanded)
    return records


def load_assets(path: str | Path | None = None) -> list[Asset]:
    """Load a UAT asset config file and normalize it into :class:`Asset` objects.

    Reuses :func:`asset_discovery.discover_from_manual` so assets flow through the
    exact same normalization + fingerprint pipeline as every other source.
    """
    cfg = load_asset_config(path)
    return assets_from_config(cfg)


def assets_from_config(cfg: dict[str, Any]) -> list[Asset]:
    """Normalize an already-loaded config dict into :class:`Asset` objects."""
    records = _asset_records_from_config(cfg)
    # Preserve asset_type in raw so classification can prefer it for routing.
    return asset_discovery.discover_from_manual(records)


# --------------------------------------------------------------------------- #
# Classification + routing
# --------------------------------------------------------------------------- #
def _connector_for(asset: Asset) -> tuple[str, str]:
    """Return (connector_module, matched_key) for an asset, or ("", "").

    Prefers an explicit ``asset_type`` (from the raw config), then the classified
    technology. Matching is case-insensitive and token-based.
    """
    candidates: list[str] = []
    raw = asset.raw or {}
    for key in ("asset_type", "type", "connector"):
        val = str(raw.get(key) or "").strip().lower()
        if val:
            candidates.append(val)
    if asset.technology:
        candidates.append(asset.technology.strip().lower())

    for cand in candidates:
        if cand in _CONNECTOR_ROUTES:
            return _CONNECTOR_ROUTES[cand], cand
        # token contains (e.g. "sharepoint online" -> "sharepoint")
        for key, module in _CONNECTOR_ROUTES.items():
            if key in cand:
                return module, key
    return "", ""


def classify_asset(asset: Asset) -> AssetClassification:
    """Classify one asset into a technology + collector route (deterministic).

    Routing precedence:
      1. **Enterprise connector** — asset_type/technology maps to a known adapter.
      2. **Baseline collector** — technology has predefined-query controls.
      3. **Unsupported** — neither; flagged for manual handling (never crashes).
    """
    reasons: list[str] = []
    technology = asset.technology or ""
    confidence = float(asset.confidence_score or 0.0)
    if technology:
        reasons.append(f"fingerprint -> {technology} ({round(confidence, 2)})")
    else:
        reasons.append("no technology fingerprinted")

    connector, matched = _connector_for(asset)
    if connector:
        reasons.append(f"connector route via '{matched}' -> {connector}")
        # Controls for the connector's technology if it exists in the catalog
        # (e.g. SonarQube), else connector-scoped with no predefined controls.
        control_ids, frameworks = _controls_for_tech(technology)
        return AssetClassification(
            asset_id=asset.asset_id, hostname=asset.hostname, environment=asset.environment,
            technology=technology, confidence=confidence,
            route=ROUTE_CONNECTOR, connector=connector,
            scope_kind="connector", scope_value=connector,
            control_ids=control_ids, frameworks=frameworks, reasons=tuple(reasons),
        )

    if technology:
        control_ids, frameworks = _controls_for_tech(technology)
        if control_ids:
            reasons.append(f"baseline collector: {len(control_ids)} predefined control(s)")
            return AssetClassification(
                asset_id=asset.asset_id, hostname=asset.hostname, environment=asset.environment,
                technology=technology, confidence=confidence,
                route=ROUTE_BASELINE, connector="",
                scope_kind="technology", scope_value=technology,
                control_ids=control_ids, frameworks=frameworks, reasons=tuple(reasons),
            )
        reasons.append("technology has no predefined controls")

    reasons.append("unsupported: no connector and no predefined controls (manual review)")
    return AssetClassification(
        asset_id=asset.asset_id, hostname=asset.hostname, environment=asset.environment,
        technology=technology, confidence=confidence,
        route=ROUTE_UNSUPPORTED, connector="",
        scope_kind="unsupported", scope_value=technology or asset.asset_id,
        control_ids=(), frameworks=(), reasons=tuple(reasons),
    )


def _controls_for_tech(technology: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Applicable control_ids + frameworks for a technology (bounded)."""
    if not technology:
        return (), ()
    control_ids = tuple(
        c.control_id for c in mapping.controls_for_technology(technology)
    )[:_MAX_CONTROLS_PER_ASSET]
    frameworks = tuple(mapping.frameworks_for_technology(technology))
    return control_ids, frameworks


def classify_assets(assets: Iterable[Asset]) -> list[AssetClassification]:
    return [classify_asset(a) for a in assets]


# --------------------------------------------------------------------------- #
# Planning
# --------------------------------------------------------------------------- #
def plan_evidence(assets: Iterable[Asset]) -> EvidencePlan:
    """Turn classified assets into a bounded, deterministic evidence plan."""
    plan = EvidencePlan()
    for classification in classify_assets(assets):
        if classification.route == ROUTE_UNSUPPORTED:
            plan.unsupported.append(classification)
            continue
        plan.jobs.append(
            PlannedJob(
                asset_id=classification.asset_id,
                technology=classification.technology,
                route=classification.route,
                connector=classification.connector,
                scope_kind=classification.scope_kind,
                scope_value=classification.scope_value,
                control_ids=classification.control_ids,
                frameworks=classification.frameworks,
            )
        )
    # Deterministic ordering: connectors first, then technology, then asset_id.
    plan.jobs.sort(key=lambda j: (j.route, j.technology.lower(), j.asset_id.lower()))
    plan.unsupported.sort(key=lambda c: c.asset_id.lower())
    return plan


# --------------------------------------------------------------------------- #
# Connector readiness (config-only; reuses the adapter registry, no live calls)
# --------------------------------------------------------------------------- #
def _connector_readiness(connector: str) -> dict[str, Any]:
    """Config-only readiness for a connector adapter (never a live call)."""
    try:
        import importlib

        mod = importlib.import_module(f"modules.operations.integrations.{connector}")
        configured = bool(mod.is_configured())
        return {
            "connector": connector,
            "configured": configured,
            "status": "configured" if configured else "not_configured",
            "masked_config": mod.masked_config(),
        }
    except Exception as exc:  # noqa: BLE001 - never break the plan on adapter import
        return {"connector": connector, "configured": False,
                "status": "adapter_error", "error": type(exc).__name__}


# --------------------------------------------------------------------------- #
# Dry run
# --------------------------------------------------------------------------- #
def dry_run(
    *,
    config_path: str | Path | None = None,
    cfg: dict[str, Any] | None = None,
    include_diagnostics: bool = True,
) -> dict[str, Any]:
    """Produce a JSON-safe dry-run report — NO queries, NO connector calls.

    Loads assets, classifies + plans them, and reports what *would* run plus
    config-only connector readiness. This is the function the CLI ``--dry-run``
    wraps and the tests assert against.
    """
    if cfg is None:
        cfg = load_asset_config(config_path)
    assets = assets_from_config(cfg)
    classifications = classify_assets(assets)
    plan = plan_evidence(assets)

    # Config-only readiness for each distinct connector in the plan.
    connectors = sorted({j.connector for j in plan.jobs if j.connector})
    readiness = {c: _connector_readiness(c) for c in connectors} if include_diagnostics else {}

    report: dict[str, Any] = {
        "mode": "dry-run",
        "config": {
            "environment": _expand(str(cfg.get("environment") or "local")),
            "asset_count": len(assets),
        },
        "assets": [a.to_dict() for a in assets],
        "classifications": [c.to_dict() for c in classifications],
        "plan": plan.to_dict(),
        "connector_readiness": readiness,
    }
    report["ok"] = True
    report["summary"] = {
        **plan.to_dict()["summary"],
        "assets_loaded": len(assets),
        "connectors_referenced": len(connectors),
        "connectors_configured": sum(1 for r in readiness.values() if r.get("configured")),
    }
    return report


# --------------------------------------------------------------------------- #
# Optional live execution (delegates to the existing evidence service; opt-in)
# --------------------------------------------------------------------------- #
def execute_plan(plan: EvidencePlan, *, executor=None, requested_by: str = "asset_scheduler",
                 run_connectors: bool = True, connector_transport=None) -> list[dict[str, Any]]:
    """Execute a plan's jobs: *baseline* via the evidence service, *connector*
    via the connector executor (opt-in evidence ingestion).

    This is NOT called by the dry-run path. It exists so a caller can, explicitly
    and outside tests, run the planned collections. An ``executor`` MUST be
    injected in any non-production/test context for baseline jobs so nothing live
    is hit implicitly.

    Connector jobs are bridged into the evidence repository via
    :func:`connector_executor.collect_for_job`, which is itself safe-by-default:
    it only performs a live call when ``ECS_CONNECTOR_EXECUTION_ENABLED`` is set
    and the adapter is configured, OR when ``connector_transport`` is injected
    (tests). Set ``run_connectors=False`` to preserve the old baseline-only
    behavior. Each returned item carries a ``kind`` of "baseline" or "connector".
    """
    from modules.audit_intelligence.services import evidence_service

    out: list[dict[str, Any]] = []
    for job in plan.jobs:
        if job.route == ROUTE_BASELINE:
            run = evidence_service.start_run(
                scope_kind="technology", scope_value=job.scope_value,
                requested_by=requested_by, executor=executor,
                control_ids=list(job.control_ids), asset_id=job.asset_id,
            )
            out.append({**run, "kind": "baseline"} if isinstance(run, dict) else run)
        elif job.route == ROUTE_CONNECTOR and run_connectors:
            from modules.audit_intelligence.services import connector_executor

            receipt = connector_executor.collect_for_job(
                job, transport=connector_transport, collected_by=requested_by,
            )
            out.append({**receipt, "kind": "connector"})
        # else: unsupported jobs (no controls + no connector) are left to manual flow
    return out
