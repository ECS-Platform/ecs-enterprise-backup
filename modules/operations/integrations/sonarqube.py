"""SonarQube integration adapter (skeleton).

Fetches project quality-gate / issue data from SonarQube and normalizes it to an
ECS AppSec-evidence shape. Config-driven; token auth; injectable transport (no
real calls in tests); secrets never logged.
"""

from __future__ import annotations

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


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("sonarqube_adapter",))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("ECS_SONARQUBE_BASE_URL"),
        "token": _base.env(str(cfg.get("token_env") or "ECS_SONARQUBE_TOKEN")),
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
        import base64

        encoded = base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")
        return {"Authorization": "Basic " + encoded}

    def _health_path(self) -> str:
        return "api/system/status"

    def fetch_issues(self, project_key: str = "", page_size: int = _base.DEFAULT_PAGE_SIZE,
                     max_items: int = 1000) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        params_base = {}
        if project_key:
            params_base["componentKeys"] = project_key
        return collect_paginated(
            lambda off, lim: self._get(
                "api/issues/search",
                {**params_base, "p": off // lim + 1, "ps": lim}),
            lambda p: list(p.get("issues", []) or []),
            normalize_issue,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    def fetch_quality_gate(self, project_key: str) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        payload, status = self._get("api/qualitygates/project_status",
                                    {"projectKey": project_key})
        if status is not None:
            return _base.error_response(SOURCE, status, f"quality gate fetch failed ({status})")
        ps = (payload or {}).get("projectStatus", {}) or {}
        return _base.ok_response(SOURCE, [normalize_quality_gate(project_key, ps)])


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


def health_check() -> dict[str, Any]:
    return SonarQubeClient().health_check()
