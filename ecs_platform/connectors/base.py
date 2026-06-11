"""Base connector contract and shared data structures."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from ecs_platform.connectors.http_client import HttpClient


class ConnectorError(RuntimeError):
    """Generic connector failure."""


class ConnectorAuthError(ConnectorError):
    """Authentication/authorization failure against the external system."""


@dataclass
class ConnectorConfig:
    """Normalized connector configuration resolved from integrations.yaml."""

    name: str
    type: str
    enabled: bool = False
    base_url: str = ""
    auth_type: str = "token"
    options: dict[str, Any] = field(default_factory=dict)
    collect: list[str] = field(default_factory=list)
    timeout_sec: int = 30
    max_retries: int = 3
    page_size: int = 100
    verify_ssl: bool = True

    def secret(self, env_key: str) -> str:
        """Resolve a secret env var name (already a name, not a value) from environment."""
        var = self.options.get(env_key) or ""
        return os.environ.get(var, "") if var else ""

    def env(self, env_key: str) -> str:
        var = self.options.get(env_key) or ""
        return os.environ.get(var, "") if var else ""


@dataclass
class ConnectorHealth:
    name: str
    type: str
    connected: bool
    authenticated: bool
    last_checked: str
    latency_ms: int = 0
    objects_collected: int = 0
    failed_syncs: int = 0
    last_sync: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "connected": self.connected,
            "authenticated": self.authenticated,
            "last_checked": self.last_checked,
            "latency_ms": self.latency_ms,
            "objects_collected": self.objects_collected,
            "failed_syncs": self.failed_syncs,
            "last_sync": self.last_sync,
            "detail": self.detail,
        }


@dataclass
class EvidenceItem:
    """A single normalized evidence artifact collected from a source system."""

    source_system: str
    source_object_id: str
    object_type: str
    title: str
    content: str
    collected_timestamp: str
    owner: str = ""
    url: str = ""
    application: str = ""
    control_mapping: list[str] = field(default_factory=list)
    framework_mapping: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_system": self.source_system,
            "source_object_id": self.source_object_id,
            "object_type": self.object_type,
            "title": self.title,
            "content": self.content,
            "collected_timestamp": self.collected_timestamp,
            "owner": self.owner,
            "url": self.url,
            "application": self.application,
            "control_mapping": self.control_mapping,
            "framework_mapping": self.framework_mapping,
            "metadata": self.metadata,
        }


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseConnector(ABC):
    """Abstract contract every ECS connector implements."""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._client: HttpClient | None = None

    # ---- shared HTTP helper ----
    def http(self) -> HttpClient:
        if self._client is None:
            self._client = HttpClient(
                base_url=self.config.base_url,
                timeout_sec=self.config.timeout_sec,
                max_retries=self.config.max_retries,
                verify_ssl=self.config.verify_ssl,
            )
            self._apply_auth(self._client)
        return self._client

    def _apply_auth(self, client: HttpClient) -> None:
        """Override per connector. Default: bearer token from configured token_env."""
        token = self.config.secret("token_env")
        if token:
            client.with_bearer(token)

    # ---- contract ----
    @abstractmethod
    def test_connection(self) -> ConnectorHealth:
        """Verify connectivity + authentication; never raises."""

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """Return high-level counts/metadata about the source system."""

    @abstractmethod
    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        """Collect normalized evidence items for the requested object types."""

    def sync(self, object_types: Iterable[str] | None = None) -> dict[str, Any]:
        """Collect evidence and return a sync summary. Persistence is handled by the engine."""
        started = utcnow()
        try:
            items = self.collect_evidence(object_types)
            return {
                "ok": True,
                "connector": self.config.name,
                "type": self.config.type,
                "started": started,
                "finished": utcnow(),
                "collected": len(items),
                "items": items,
            }
        except ConnectorError as exc:
            return {
                "ok": False,
                "connector": self.config.name,
                "type": self.config.type,
                "started": started,
                "finished": utcnow(),
                "error": str(exc),
                "items": [],
            }

    def health_check(self) -> ConnectorHealth:
        return self.test_connection()

    # ---- helpers for subclasses ----
    def _health(self, *, connected: bool, authenticated: bool, latency_ms: int = 0, detail: str = "") -> ConnectorHealth:
        return ConnectorHealth(
            name=self.config.name,
            type=self.config.type,
            connected=connected,
            authenticated=authenticated,
            last_checked=utcnow(),
            latency_ms=latency_ms,
            detail=detail,
        )

    def _disabled_health(self, reason: str = "disabled or not configured") -> ConnectorHealth:
        return self._health(connected=False, authenticated=False, detail=reason)
