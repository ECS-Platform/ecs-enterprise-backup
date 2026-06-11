"""Minimal dependency-free HTTP client for connectors (stdlib urllib).

Avoids adding a hard runtime dependency so the existing app never breaks on import.
Supports bearer/basic/header auth, JSON, retries with backoff, and timeouts.
"""

from __future__ import annotations

import base64
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import ssl
from dataclasses import dataclass, field
from typing import Any


class HttpError(RuntimeError):
    def __init__(self, status: int, message: str, body: str = ""):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


@dataclass
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: str

    def json(self) -> Any:
        if not self.body:
            return None
        return json.loads(self.body)


@dataclass
class HttpClient:
    base_url: str = ""
    timeout_sec: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    default_headers: dict[str, str] = field(default_factory=dict)

    def _context(self) -> ssl.SSLContext | None:
        if self.base_url.startswith("https") and not self.verify_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        return None

    def with_bearer(self, token: str) -> "HttpClient":
        if token:
            self.default_headers["Authorization"] = f"Bearer {token}"
        return self

    def with_basic(self, user: str, password: str) -> "HttpClient":
        if user or password:
            raw = base64.b64encode(f"{user}:{password}".encode()).decode()
            self.default_headers["Authorization"] = f"Basic {raw}"
        return self

    def with_header(self, key: str, value: str) -> "HttpClient":
        if value:
            self.default_headers[key] = value
        return self

    def _url(self, path: str, params: dict[str, Any] | None) -> str:
        url = path if path.startswith("http") else f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(clean, doseq=True)}"
        return url

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        url = self._url(path, params)
        data = None
        merged = dict(self.default_headers)
        if headers:
            merged.update(headers)
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            merged.setdefault("Content-Type", "application/json")
        merged.setdefault("Accept", "application/json")

        last_exc: Exception | None = None
        for attempt in range(1, max(1, self.max_retries) + 1):
            req = urllib.request.Request(url, data=data, method=method.upper(), headers=merged)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_sec, context=self._context()) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    return HttpResponse(resp.status, dict(resp.headers), body)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
                # Retry on transient server errors only.
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    last_exc = exc
                    continue
                raise HttpError(exc.code, exc.reason or "request failed", body) from exc
            except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise HttpError(0, f"connection error: {exc}") from exc
        raise HttpError(0, f"request failed after retries: {last_exc}")

    def get(self, path: str, **kw) -> HttpResponse:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> HttpResponse:
        return self.request("POST", path, **kw)
