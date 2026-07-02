"""SharePoint Online connector (Graph API) — credential-optional."""

from __future__ import annotations

from typing import Any, Iterable

from ecs_platform.connectors._msgraph import MsGraphConnector
from ecs_platform.connectors.base import ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpError


class SharePointConnector(MsGraphConnector):
    DEFAULT_TYPES = ["policies", "documents", "evidence_files"]

    @property
    def _site_id(self) -> str:
        return self.config.secret("site_id_env")

    def test_connection(self) -> ConnectorHealth:
        if not self._site_id:
            return self._disabled_health("set SHAREPOINT_SITE_ID + MS Graph credentials and enable")
        return self._graph_health(f"/sites/{self._site_id}")

    def get_metadata(self) -> dict[str, Any]:
        return {"configured": bool(self._msgraph_configured() and self._site_id)}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        if not (self._msgraph_configured() and self._site_id):
            return []
        items: list[EvidenceItem] = []
        try:
            drive = self._graph().get(f"/sites/{self._site_id}/drive/root/children")
            children = (drive.json() or {}).get("value", [])
        except (HttpError, OSError):
            return []
        for doc in children[: self.config.page_size]:
            items.append(EvidenceItem(
                source_system="sharepoint", source_object_id=doc.get("id", ""), object_type="document",
                title=doc.get("name", ""), content=doc.get("name", ""), collected_timestamp=utcnow(),
                url=doc.get("webUrl", ""), control_mapping=["documentation", "policy"],
                metadata={"size": doc.get("size")},
            ))
        return items
