"""AWS cloud-posture integration adapter (skeleton).

Collects account/compliance posture evidence (e.g. Security Hub findings, Config
compliance) via a configurable HTTP endpoint using the shared transport
abstraction — no AWS SDK (boto3) dependency is added. Credentials come from env /
YAML only; the adapter degrades to ``not_configured`` when absent and makes no
live call unless a transport is injected or connector execution is enabled
upstream. Secrets are never logged.

This intentionally uses the existing ECS ``BaseAdapter``/transport contract so it
plugs into the connector registry, workbench, and scheduler exactly like the other
connectors, without introducing cloud SDKs or a parallel framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations._base import BaseAdapter, Transport, mask_secret

SOURCE = "aws"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("aws", "aws_connector"))
    return {
        # Optional posture/collector endpoint (e.g. a Security Hub export proxy).
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("AWS_POSTURE_BASE_URL"),
        "region": (str(cfg.get("region")) if cfg.get("region") else "")
        or _base.env("AWS_REGION"),
        "access_key_id": _base.env(str(cfg.get("access_key_env") or "AWS_ACCESS_KEY_ID")),
        "secret_access_key": _base.env(str(cfg.get("secret_key_env") or "AWS_SECRET_ACCESS_KEY")),
        "account_id": (str(cfg.get("account_id")) if cfg.get("account_id") else "")
        or _base.env("AWS_ACCOUNT_ID"),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("AWS_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("AWS_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["access_key_id"] and c["secret_access_key"] and c["region"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "AWS",
        "base_url_configured": bool(cfg.get("base_url")),
        "region": cfg.get("region") or "",
        "access_key_id": mask_secret(cfg.get("access_key_id")),
        "secret_access_key": mask_secret(cfg.get("secret_access_key")),
        "account_id": mask_secret(cfg.get("account_id")),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("access_key_id") and cfg.get("secret_access_key") and cfg.get("region")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class AWSClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("access_key_id") and c.get("secret_access_key") and c.get("region"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def auth_headers(self) -> dict:
        # A real deployment signs requests (SigV4) or fronts a collector proxy with
        # a bearer token; here we pass a non-secret region hint only (creds are
        # never placed in a header/log). The injected production transport owns
        # actual signing.
        region = self.config.get("region")
        return {"X-Amz-Region": region} if region else {}

    def _health_path(self) -> str:
        return "posture/health"

    def fetch_findings(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                       max_items: int = 1000) -> dict[str, Any]:
        """Security-posture findings (GET {base}/securityhub/findings)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not self.base_url():
            return _base.error_response(SOURCE, "not_configured",
                                        "AWS_POSTURE_BASE_URL (collector endpoint) is required for live fetch")
        return _base.collect_paginated(
            lambda off, lim: self._get("securityhub/findings", {"offset": off, "limit": lim}),
            lambda p: list(p.get("Findings", p.get("items", [])) or []) if isinstance(p, dict) else [],
            normalize_finding,
            source=SOURCE, page_size=page_size, max_items=max_items,
        )

    def fetch_config_compliance(self) -> dict[str, Any]:
        """AWS Config compliance summary (GET {base}/config/compliance)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        if not self.base_url():
            return _base.error_response(SOURCE, "not_configured",
                                        "AWS_POSTURE_BASE_URL (collector endpoint) is required for live fetch")
        payload, status = self._get("config/compliance")
        if status is not None:
            return _base.error_response(SOURCE, status, f"config compliance fetch failed ({status})")
        items = (payload or {}).get("items", []) or []
        return _base.ok_response(SOURCE, [normalize_compliance(c) for c in items])


def normalize_finding(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "finding_id": record.get("Id", record.get("id", "")),
        "title": record.get("Title", record.get("title", "")),
        "severity": (record.get("Severity", {}) or {}).get("Label",
                     record.get("severity", "")) if isinstance(record.get("Severity"), dict)
        else record.get("severity", ""),
        "resource": (record.get("Resources", [{}]) or [{}])[0].get("Id", "")
        if record.get("Resources") else record.get("resource", ""),
        "compliance_status": (record.get("Compliance", {}) or {}).get("Status", ""),
        "region": record.get("Region", ""),
        "evidence_type": "aws_finding",
    }


def normalize_compliance(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "rule": record.get("ConfigRuleName", record.get("rule", "")),
        "compliance_type": record.get("ComplianceType", record.get("compliance_type", "")),
        "resource_id": record.get("ResourceId", record.get("resource_id", "")),
        "evidence_type": "aws_config_compliance",
    }


def health_check() -> dict[str, Any]:
    return AWSClient().health_check()
