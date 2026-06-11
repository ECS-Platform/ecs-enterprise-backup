"""Microsoft Teams connector (Graph API) — credential-optional."""

from __future__ import annotations

from typing import Any, Iterable

from ecs_platform.connectors._msgraph import MsGraphConnector
from ecs_platform.connectors.base import ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpError


class TeamsConnector(MsGraphConnector):
    DEFAULT_TYPES = ["governance_channels", "approval_messages"]

    def test_connection(self) -> ConnectorHealth:
        return self._graph_health("/teams")

    def get_metadata(self) -> dict[str, Any]:
        return {"configured": self._msgraph_configured()}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        if not self._msgraph_configured():
            return []
        items: list[EvidenceItem] = []
        try:
            teams = (self._graph().get("/teams").json() or {}).get("value", [])
        except (HttpError, OSError):
            return []
        for team in teams[: self.config.page_size]:
            items.append(EvidenceItem(
                source_system="teams", source_object_id=team.get("id", ""), object_type="governance_channel",
                title=team.get("displayName", ""), content=team.get("description", "") or team.get("displayName", ""),
                collected_timestamp=utcnow(), control_mapping=["governance", "approvals"],
            ))
        return items
