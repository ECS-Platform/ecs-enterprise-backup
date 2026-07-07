"""SonarQube integration adapter.

Fetches project quality-gate / issue / measures data from SonarQube and
normalizes it to ECS AppSec-evidence shapes. Config-driven; token auth (token as
Basic username with an empty password); injectable transport (no real calls in
tests); secrets never logged.

Backward compatibility: ``fetch_issues`` / ``fetch_quality_gate`` and the existing
normalizers keep their behavior/keys. New methods (``fetch_projects`` /
``fetch_measures``) and ``normalize_project`` / ``normalize_measure`` are additive.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations._base import (
    BaseAdapter,
    Transport,
    collect_paginated,
    mask_secret,
)

SOURCE = "sonarqube"
#: Default measures pulled when no explicit metric list is requested.
DEFAULT_METRICS = (
    "bugs", "vulnerabilities", "code_smells", "coverage",
    "duplicated_lines_density", "ncloc", "sqale_rating",
)


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("sonarqube_adapter",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_SONARQUBE_BASE_URL"),
        "token": _base.env(str(cfg.get("token_env") or "ECS_SONARQUBE_TOKEN")),
        "project_key": (str(cfg.get("project_key")) if cfg.get("project_key") else "")
        or _base.env("ECS_SONARQUBE_PROJECT_KEY"),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("ECS_SONARQUBE_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC,
        ),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("ECS_SONARQUBE_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES,
        ),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["base_url"] and c["token"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "SonarQube",
        "base_url_configured": bool(cfg.get("base_url")),
        "token": mask_secret(cfg.get("token")),
        "project_key": cfg.get("project_key") or "",
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("base_url") and cfg.get("token")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class SonarQubeClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("base_url") and c.get("token"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def auth_headers(self) -> dict:
        # SonarQube authenticates a user token as the Basic username with an EMPTY
        # password (i.e. "<token>:"). We build it directly so the empty-password
        # convention is honoured; the token is never logged or sent as a param.
        token = self.config.get("token") or ""
        if not token:
            return {}
        encoded = base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")
        return {"Authorization": "Basic " + encoded}

    def _health_path(self) -> str:
        return "api/system/status"

    # ---- projects --------------------------------------------------------- #
    def fetch_projects(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                       max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        return collect_paginated(
            lambda off, lim: self._get(
                "api/projects/search", {"p": off // lim + 1, "ps": lim}),
            lambda p: list(p.get("components", []) or []),
            normalize_project,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    # ---- issues ----------------------------------------------------------- #
    def fetch_issues(self, project_key: str = "", severities: str = "",
                     page_size: int = _base.DEFAULT_PAGE_SIZE,
                     max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        project_key = project_key or self.config.get("project_key") or ""
        params_base: dict[str, Any] = {}
        if project_key:
            params_base["componentKeys"] = project_key
        if severities:
            params_base["severities"] = severities
        return collect_paginated(
            lambda off, lim: self._get(
                "api/issues/search",
                {**params_base, "p": off // lim + 1, "ps": lim}),
            lambda p: list(p.get("issues", []) or []),
            normalize_issue,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    # ---- quality gate ----------------------------------------------------- #
    def fetch_quality_gate(self, project_key: str = "") -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        project_key = project_key or self.config.get("project_key") or ""
        payload, status = self._get("api/qualitygates/project_status",
                                    {"projectKey": project_key})
        if status is not None:
            return _base.error_response(SOURCE, status, f"quality gate fetch failed ({status})")
        ps = (payload or {}).get("projectStatus", {}) or {}
        return _base.ok_response(SOURCE, [normalize_quality_gate(project_key, ps)])

    # ---- measures --------------------------------------------------------- #
    def fetch_measures(self, project_key: str = "", metrics: Any = None) -> dict[str, Any]:
        """Fetch component measures (metrics) for a project."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        project_key = project_key or self.config.get("project_key") or ""
        if not project_key:
            return _base.error_response(SOURCE, "http_error", "project_key is required")
        metric_keys = metrics or DEFAULT_METRICS
        if isinstance(metric_keys, (list, tuple)):
            metric_keys = ",".join(metric_keys)
        payload, status = self._get(
            "api/measures/component",
            {"component": project_key, "metricKeys": metric_keys})
        if status is not None:
            return _base.error_response(SOURCE, status, f"measures fetch failed ({status})")
        component = (payload or {}).get("component", {}) or {}
        measures = list(component.get("measures", []) or [])
        return _base.ok_response(SOURCE, [normalize_measure(project_key, measures)])


# --------------------------------------------------------------------------- #
# Normalizers
# --------------------------------------------------------------------------- #
def normalize_project(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "project_key": record.get("key", ""),
        "project_name": record.get("name", ""),
        "qualifier": record.get("qualifier", ""),
        "last_analysis": record.get("lastAnalysisDate", ""),
        "evidence_type": "sonarqube_project",
    }


def normalize_issue(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_key": record.get("key", ""),
        "rule": record.get("rule", ""),
        "severity": record.get("severity", ""),
        "type": record.get("type", ""),
        "component": record.get("component", ""),
        "status": record.get("status", ""),
        "source": SOURCE,
    }


def normalize_quality_gate(project_key: str, ps: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_key": project_key,
        "status": ps.get("status", ""),
        "conditions": len(ps.get("conditions", []) or []),
        "source": SOURCE,
    }


def _measure_map(measures: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for m in measures or []:
        if isinstance(m, dict) and m.get("metric") is not None:
            out[m["metric"]] = m.get("value", m.get("period", {}).get("value", ""))
    return out


def normalize_measure(project_key: str, measures: list[dict[str, Any]]) -> dict[str, Any]:
    m = _measure_map(measures)
    return {
        "source": SOURCE,
        "project_key": project_key,
        "bugs": m.get("bugs", ""),
        "vulnerabilities": m.get("vulnerabilities", ""),
        "code_smells": m.get("code_smells", ""),
        "coverage": m.get("coverage", ""),
        "duplicated_lines_density": m.get("duplicated_lines_density", ""),
        "ncloc": m.get("ncloc", ""),
        "measures": m,
        "evidence_type": "sonarqube_measures",
    }


def health_check() -> dict[str, Any]:
    return SonarQubeClient().health_check()
