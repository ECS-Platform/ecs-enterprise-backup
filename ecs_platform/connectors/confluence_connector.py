"""Confluence connector (Atlassian) — real REST endpoints, credential-optional."""

from __future__ import annotations

import re
import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError

_TAGS = re.compile(r"<[^>]+>")


class ConfluenceConnector(BaseConnector):
    DEFAULT_TYPES = ["spaces", "pages", "policies"]

    def _apply_auth(self, client: HttpClient) -> None:
        user = self.config.secret("username_env")
        token = self.config.secret("token_env")
        if user and token:
            client.with_basic(user, token)
        elif token:
            client.with_bearer(token)

    def _configured(self) -> bool:
        return bool(self.config.enabled and self.config.base_url and self.config.secret("token_env"))

    def test_connection(self) -> ConnectorHealth:
        if not self._configured():
            return self._disabled_health("set CONFLUENCE_URL + CONFLUENCE_USER + CONFLUENCE_TOKEN and enable")
        start = time.time()
        try:
            resp = self.http().get("/wiki/rest/api/space", params={"limit": 1})
            return self._health(connected=True, authenticated=resp.status == 200,
                                latency_ms=int((time.time() - start) * 1000), detail="authenticated")
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def get_metadata(self) -> dict[str, Any]:
        if not self._configured():
            return {"configured": False}
        try:
            data = self.http().get("/wiki/rest/api/space", params={"limit": self.config.page_size}).json() or {}
            return {"configured": True, "space_count": len(data.get("results", []))}
        except HttpError:
            return {"configured": True, "space_count": 0}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        if not self._configured():
            return []
        wanted = set(object_types or self.config.collect or self.DEFAULT_TYPES)
        items: list[EvidenceItem] = []
        if {"pages", "policies", "architecture_documents"} & wanted:
            items.extend(self._pages())
        return items

    def _pages(self) -> list[EvidenceItem]:
        try:
            resp = self.http().get("/wiki/rest/api/content",
                                   params={"type": "page", "limit": self.config.page_size,
                                           "expand": "body.storage,space,version"})
        except HttpError:
            return []
        out: list[EvidenceItem] = []
        for page in (resp.json() or {}).get("results", []):
            body = (((page.get("body") or {}).get("storage") or {}).get("value")) or ""
            text = _TAGS.sub(" ", body)
            out.append(EvidenceItem(
                source_system="confluence", source_object_id=page.get("id", ""),
                object_type="page", title=page.get("title", ""), content=text[:8000],
                collected_timestamp=utcnow(), application=(page.get("space") or {}).get("key", ""),
                url=f"{self.config.base_url.rstrip('/')}/wiki{(page.get('_links') or {}).get('webui', '')}",
                control_mapping=["documentation", "policy"], framework_mapping=["ISO27001-A.5"],
            ))
        return out
