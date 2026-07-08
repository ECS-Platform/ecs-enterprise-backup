"""Azure cloud-posture integration adapter (skeleton).

Collects Microsoft Defender for Cloud / Azure Policy compliance via the Azure
Management REST API using the shared transport abstraction — no azure SDK is
added. Uses OAuth2 client-credentials (tenant/client/secret) to obtain a bearer
token (mirroring the existing MS Graph auth pattern, cached per instance).
Credentials come from env / YAML only; the adapter degrades to ``not_configured``
when absent and makes no live call unless a transport is injected. Secrets are
never logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations._base import (
    BaseAdapter, Transport, bearer_auth_header, mask_secret,
)

SOURCE = "azure"

DEFAULT_AUTHORITY = "https://login.microsoftonline.com"
DEFAULT_MGMT_BASE = "https://management.azure.com"
DEFAULT_SCOPE = "https://management.azure.com/.default"
TOKEN_URL_TEMPLATE = "{authority}/{tenant_id}/oauth2/v2.0/token"


def get_config() -> dict[str, Any]:
    cfg = _base.yaml_block(("azure", "azure_connector"))
    return {
        "base_url": (str(cfg.get("base_url")) if cfg.get("base_url") else "")
        or _base.env("AZURE_MGMT_BASE_URL") or DEFAULT_MGMT_BASE,
        "tenant_id": (str(cfg.get("tenant_id")) if cfg.get("tenant_id") else "")
        or _base.env("AZURE_TENANT_ID"),
        "client_id": (str(cfg.get("client_id")) if cfg.get("client_id") else "")
        or _base.env("AZURE_CLIENT_ID"),
        "client_secret": _base.env(str(cfg.get("client_secret_env") or "AZURE_CLIENT_SECRET")),
        "subscription_id": (str(cfg.get("subscription_id")) if cfg.get("subscription_id") else "")
        or _base.env("AZURE_SUBSCRIPTION_ID"),
        "authority_url": (str(cfg.get("authority_url")) if cfg.get("authority_url") else "")
        or _base.env("AZURE_AUTHORITY_URL") or DEFAULT_AUTHORITY,
        "scope": (str(cfg.get("scope")) if cfg.get("scope") else "")
        or _base.env("AZURE_SCOPE") or DEFAULT_SCOPE,
        "access_token": _base.env(str(cfg.get("access_token_env") or "AZURE_ACCESS_TOKEN")),
        "timeout_sec": _base.safe_int(
            cfg.get("timeout_sec") or _base.env("AZURE_TIMEOUT_SECONDS"),
            _base.DEFAULT_TIMEOUT_SEC),
        "max_retries": _base.safe_int(
            cfg.get("max_retries") or _base.env("AZURE_MAX_RETRIES"),
            _base.DEFAULT_MAX_RETRIES),
    }


def is_configured() -> bool:
    c = get_config()
    return bool(c["tenant_id"] and c["client_id"] and c["client_secret"] and c["subscription_id"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Azure",
        "base_url_configured": bool(cfg.get("base_url")),
        "tenant_id": mask_secret(cfg.get("tenant_id")),
        "client_id": mask_secret(cfg.get("client_id")),
        "client_secret": mask_secret(cfg.get("client_secret")),
        "subscription_id": mask_secret(cfg.get("subscription_id")),
        "access_token": mask_secret(cfg.get("access_token")),
        "scope": cfg.get("scope"),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("tenant_id") and cfg.get("client_id")
                      and cfg.get("client_secret") and cfg.get("subscription_id")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class AzureClient(BaseAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None
    _cached_token: Optional[str] = field(default=None, repr=False, compare=False)
    _token_attempted: bool = field(default=False, repr=False, compare=False)

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("tenant_id") and c.get("client_id")
                    and c.get("client_secret") and c.get("subscription_id"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def _token_url(self) -> str:
        authority = str(self.config.get("authority_url") or DEFAULT_AUTHORITY).rstrip("/")
        return TOKEN_URL_TEMPLATE.format(authority=authority,
                                         tenant_id=self.config.get("tenant_id", ""))

    def authenticate(self) -> Optional[str]:
        """OAuth2 client-credentials token (cached per instance; never logged)."""
        if self.config.get("access_token"):
            return str(self.config["access_token"])
        if self._cached_token or self._token_attempted:
            return self._cached_token
        self._token_attempted = True
        if self.transport is None:
            return None  # skeleton: no live token exchange without a transport
        payload, status = _base.call_with_retry(
            self.transport, "POST", self._token_url(),
            {"Accept": "application/json",
             "Content-Type": "application/x-www-form-urlencoded"},
            {"grant_type": "client_credentials",
             "client_id": self.config.get("client_id", ""),
             "client_secret": self.config.get("client_secret", ""),
             "scope": self.config.get("scope") or DEFAULT_SCOPE},
            max_retries=self.max_retries(), backoff_base=self.backoff_base_sec(),
            timeout=self.timeout_sec())
        if status is None:
            token = (payload or {}).get("access_token")
            if token:
                self._cached_token = str(token)
        return self._cached_token

    def auth_headers(self) -> dict:
        return bearer_auth_header(self.config.get("access_token") or self._cached_token)

    def _get(self, path: str, params: Optional[dict] = None):
        self.authenticate()  # ensure a (mock/real) token before the call
        return super()._get(path, params)

    def _health_path(self) -> str:
        sub = self.config.get("subscription_id", "")
        return f"subscriptions/{sub}?api-version=2020-01-01"

    def fetch_security_assessments(self, max_items: int = 1000) -> dict[str, Any]:
        """Defender for Cloud assessments (GET .../providers/Microsoft.Security/assessments)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        sub = self.config.get("subscription_id", "")
        payload, status = self._get(
            f"subscriptions/{sub}/providers/Microsoft.Security/assessments",
            {"api-version": "2020-01-01"})
        if status is not None:
            return _base.error_response(SOURCE, status, f"assessments fetch failed ({status})")
        items = list((payload or {}).get("value", []) or [])
        return _base.ok_response(SOURCE, [normalize_assessment(a) for a in items[:max_items]])

    def fetch_policy_states(self, max_items: int = 1000) -> dict[str, Any]:
        """Azure Policy compliance states (GET .../Microsoft.PolicyInsights/policyStates)."""
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        sub = self.config.get("subscription_id", "")
        payload, status = self._get(
            f"subscriptions/{sub}/providers/Microsoft.PolicyInsights/policyStates/latest/queryResults",
            {"api-version": "2019-10-01"})
        if status is not None:
            return _base.error_response(SOURCE, status, f"policy states fetch failed ({status})")
        items = list((payload or {}).get("value", []) or [])
        return _base.ok_response(SOURCE, [normalize_policy_state(p) for p in items[:max_items]])


def normalize_assessment(record: dict[str, Any]) -> dict[str, Any]:
    props = record.get("properties", {}) or {}
    status = props.get("status", {}) or {}
    return {
        "source": SOURCE,
        "assessment_id": record.get("id", record.get("name", "")),
        "display_name": props.get("displayName", ""),
        "status": status.get("code", ""),
        "severity": status.get("severity", props.get("metadata", {}).get("severity", "")),
        "resource": props.get("resourceDetails", {}).get("Id", ""),
        "evidence_type": "azure_security_assessment",
    }


def normalize_policy_state(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "policy_definition": record.get("policyDefinitionName", record.get("policy_definition", "")),
        "compliance_state": record.get("complianceState", record.get("compliance_state", "")),
        "resource_id": record.get("resourceId", record.get("resource_id", "")),
        "evidence_type": "azure_policy_state",
    }


def health_check() -> dict[str, Any]:
    return AzureClient().health_check()
