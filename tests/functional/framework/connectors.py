"""Connector / integration capabilities over the real ECS connector API.

  GET  /api/connectors                                   list + enabled/config status
  GET  /api/connectors/{name}/config-status
  POST /api/connectors/{name}/{health-check|dry-run|parser-test}
  POST /api/connectors/{name}/collect?application=&framework=&control=&max_items=&user=   (live call only when ECS allows it)
  GET  /api/audit/integrations[/health|/{name}/health]    integration health
  POST /api/platform/sync/{connector}                     admin sync (can_admin_platform)
Connector names/types are those in ecs_platform/connectors (sharepoint, servicenow, jira, github, ...).
Live collection is gated by the ``live_connectors`` feature flag so no external system is touched unintentionally.
"""

from __future__ import annotations

from typing import Any

from .api_client import ApiResponse, EcsApiClient
from .data_factory import DataFactory
from .errors import CapabilityBlocked


class ConnectorHelper:
    def __init__(self, api: EcsApiClient, data: DataFactory) -> None:
        self.api, self.data = api, data

    def list(self) -> Any:
        return self.api.get_json("/api/connectors")

    def names(self) -> list[str]:
        body = self.list()
        rows = body.get("connectors", body) if isinstance(body, dict) else body
        out = []
        for r in rows if isinstance(rows, list) else []:
            out.append(str(r.get("name") if isinstance(r, dict) else r))
        return out

    def require_available(self, name: str) -> None:
        if name.lower() not in {n.lower() for n in self.names()}:
            raise CapabilityBlocked(f"Connector '{name}' is not registered in this ECS environment.", requires=f"connector {name}")

    def config_status(self, name: str) -> ApiResponse:
        return self.api.get(f"/api/connectors/{name}/config-status")

    def health_check(self, name: str) -> ApiResponse:
        return self.api.post(f"/api/connectors/{name}/health-check")

    def dry_run(self, name: str) -> ApiResponse:
        return self.api.post(f"/api/connectors/{name}/dry-run")

    def parser_test(self, name: str) -> ApiResponse:
        return self.api.post(f"/api/connectors/{name}/parser-test")

    def collect(self, name: str, *, max_items: int = 5, persona: str | None = None, live: bool = False, **scope: str) -> ApiResponse:
        if live and not self.api.cfg.feature("live_connectors"):
            raise CapabilityBlocked("Live connector collection requires ECS_FT_LIVE_CONNECTORS=true and configured credentials.",
                                    requires="live_connectors flag")
        client = self.api.as_persona(persona) if persona else self.api
        return client.post(f"/api/connectors/{name}/collect",
                           params={"application": scope.get("application", self.data.application()),
                                   "framework": scope.get("framework", self.data.framework()),
                                   "control": scope.get("control", self.data.control()), "max_items": str(max_items),
                                   "user": self.api.identity.get("user", "connector_executor")})

    def integrations_health(self) -> ApiResponse:
        return self.api.get("/api/audit/integrations/health")

    def integration_health(self, name: str) -> ApiResponse:
        return self.api.get(f"/api/audit/integrations/{name}/health")

    def platform_sync(self, name: str, persona: str = "system_admin") -> ApiResponse:
        return self.api.as_persona(persona).post(f"/api/platform/sync/{name}")

    def source_traceability(self, evidence_row: dict[str, Any]) -> dict[str, Any]:
        """Source-linking fields on a collected evidence row (source system, object id, URL) for assert_traceability."""
        keys = ("source", "source_system", "source_connector", "connector", "source_object_id", "url", "object_reference")
        return {k: evidence_row[k] for k in keys if evidence_row.get(k)}
