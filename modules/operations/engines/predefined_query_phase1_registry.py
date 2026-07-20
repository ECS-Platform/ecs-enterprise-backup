"""Phase-1 predefined query registry — configuration-first MVP subset.

Loads ``config/predefined_query_phase1_registry.yaml`` and exposes helpers used
by ``predefined_queries_engine`` to gate live execution without duplicating query
definitions.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REGISTRY_PATH = _REPO_ROOT / "config" / "predefined_query_phase1_registry.yaml"

# Registry technology -> predefined_query_targets block key (environment YAML).
_TARGET_KEY_BY_TECH: dict[str, str] = {
    "PostgreSQL": "postgresql",
    "YugabyteDB": "yugabyte",
    "Aurora MySQL": "aurora_mysql",
    "Oracle": "oracle",
    "Linux": "linux",
    "Red Hat Enterprise Linux 8.x": "rhel8",
    "Red Hat Enterprise Linux 9.x": "rhel9",
    "NGINX": "nginx",
    "Apache HTTPD": "apache",
    "Tomcat": "tomcat",
    "SonarQube": "sonarqube",
    "Trivy": "trivy",
    "GitLeaks": "gitleaks",
    "Kubernetes": "kubernetes",
    "OpenShift": "openshift",
}


@lru_cache(maxsize=1)
def load_phase1_registry() -> dict[str, Any]:
    if not _REGISTRY_PATH.is_file():
        return {}
    try:
        import yaml

        with _REGISTRY_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def phase1_technologies() -> frozenset[str]:
    return frozenset(load_phase1_registry().get("technologies") or [])


def deferred_technologies() -> frozenset[str]:
    return frozenset(load_phase1_registry().get("deferred_technologies") or [])


def phase1_selected_ids() -> frozenset[str]:
    return frozenset(load_phase1_registry().get("selected_control_ids") or [])


def technology_connector_spec(technology: str) -> dict[str, Any]:
    specs = load_phase1_registry().get("technology_connectors") or {}
    spec = specs.get(technology)
    return dict(spec) if isinstance(spec, dict) else {}


def is_phase1_selected(control_id: str) -> bool:
    return str(control_id or "") in phase1_selected_ids()


def is_phase1_deferred(control: dict[str, Any]) -> bool:
    tech = str(control.get("technology") or "")
    cid = str(control.get("control_id") or "")
    if tech in deferred_technologies() or tech == "Unknown":
        return True
    if tech and tech not in phase1_technologies():
        return True
    return cid not in phase1_selected_ids()


def defer_reason(control: dict[str, Any]) -> str:
    tech = str(control.get("technology") or "")
    cid = str(control.get("control_id") or "")
    if tech in deferred_technologies():
        return f"{tech} deferred from Phase-1 MVP delivery"
    if tech == "Unknown":
        return "Unsupported generic technology — deferred from Phase-1"
    if tech and tech not in phase1_technologies():
        return f"{tech} not in approved Phase-1 technology list"
    if cid and cid not in phase1_selected_ids():
        return "Not selected for Phase-1 MVP high-value subset"
    return ""


def _resolved_target_block(target_key: str) -> dict[str, Any]:
    if not target_key:
        return {}
    try:
        from modules.operations.engines.query_connectors import get_predefined_target

        block = get_predefined_target(target_key)
        return dict(block) if isinstance(block, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _non_empty(value: Any) -> bool:
    s = str(value or "").strip()
    return bool(s) and not s.startswith("${")


def has_configured_target(technology: str) -> bool:
    """True when the active environment exposes a usable target for the technology."""
    spec = technology_connector_spec(technology)
    target_key = spec.get("target_key") or _TARGET_KEY_BY_TECH.get(technology, "")
    if not target_key:
        return False
    block = _resolved_target_block(str(target_key))
    if not block:
        return False

    if technology in ("Kubernetes", "OpenShift"):
        import os

        kube = block.get("kubeconfig") or os.environ.get(
            "ECS_KUBECONFIG" if technology == "Kubernetes" else "ECS_OPENSHIFT_KUBECONFIG", ""
        )
        binary = block.get("binary") or ("kubectl" if technology == "Kubernetes" else "oc")
        return _non_empty(binary) and (_non_empty(kube) or os.environ.get("DEMO_MODE") == "true")

    if technology == "GitLeaks":
        import os
        from pathlib import Path

        scan = block.get("scan_path") or os.environ.get("ECS_GITLEAKS_SCAN_PATH", "")
        if _non_empty(scan) and Path(str(scan)).is_dir():
            return True
        demo = _REPO_ROOT / "demo-data" / "gitleaks-sample"
        return demo.is_dir()

    if technology in ("Linux", "Red Hat Enterprise Linux 8.x", "Red Hat Enterprise Linux 9.x",
                      "NGINX", "Apache HTTPD", "Tomcat"):
        return _non_empty(block.get("container"))

    if technology in ("SonarQube", "Trivy"):
        return _non_empty(block.get("base_url")) or _non_empty(block.get("image"))

    # SQL engines — host + port in environment config (defaults are acceptable).
    return _non_empty(block.get("host"))


def resolve_registry_entry(control: dict[str, Any]) -> dict[str, Any]:
    """Return registry fields for a catalog control (no query duplication)."""
    tech = str(control.get("technology") or "")
    cid = str(control.get("control_id") or "")
    spec = technology_connector_spec(tech)
    deferred = is_phase1_deferred(control)
    selected = is_phase1_selected(cid) and not deferred
    target_required = bool(spec.get("target_required", False))
    target_ok = has_configured_target(tech) if target_required else True
    return {
        "control_id": cid,
        "technology": tech,
        "enabled": selected,
        "execution_mode": spec.get("execution_mode") or "",
        "connector": spec.get("connector") or "",
        "target_required": target_required,
        "target_configured": target_ok,
        "phase": "Deferred" if deferred else "Phase1",
        "phase1_selected": selected,
        "defer_reason": defer_reason(control) if deferred else "",
    }


def registry_rows() -> list[dict[str, Any]]:
    from modules.operations.engines.predefined_queries_engine import get_all_controls

    return [resolve_registry_entry(c) for c in get_all_controls() if c.get("predefined")]
