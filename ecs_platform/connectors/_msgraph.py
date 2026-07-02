"""Shared Microsoft Graph OAuth2 (client credentials) base for Teams/SharePoint."""

from __future__ import annotations

import time
import urllib.parse
import urllib.request
from typing import Any

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth
from ecs_platform.connectors.http_client import HttpClient, HttpError


class MsGraphConnector(BaseConnector):
    """Base for Graph-backed connectors. Acquires app-only tokens on demand."""

    def _msgraph_configured(self) -> bool:
        return bool(
            self.config.enabled
            and self.config.secret("tenant_id_env")
            and self.config.secret("client_id_env")
            and self.config.secret("client_secret_env")
        )

    def _acquire_token(self) -> str:
        tenant = self.config.secret("tenant_id_env")
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.config.secret("client_id_env"),
            "client_secret": self.config.secret("client_secret_env"),
            "scope": "https://graph.microsoft.com/.default",
        }).encode()
        url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
            import json
            return json.loads(resp.read().decode()).get("access_token", "")

    def _graph(self) -> HttpClient:
        client = HttpClient(base_url=self.config.base_url, timeout_sec=self.config.timeout_sec,
                            max_retries=self.config.max_retries, verify_ssl=self.config.verify_ssl)
        return client.with_bearer(self._acquire_token())

    def _graph_health(self, probe_path: str) -> ConnectorHealth:
        if not self._msgraph_configured():
            return self._disabled_health("set MS_TENANT_ID + MS_CLIENT_ID + MS_CLIENT_SECRET and enable")
        start = time.time()
        try:
            resp = self._graph().get(probe_path)
            return self._health(connected=True, authenticated=resp.status == 200,
                                latency_ms=int((time.time() - start) * 1000), detail="authenticated")
        except (HttpError, OSError) as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))
