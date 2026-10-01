"""Reusable ECS API client (GET/POST/PUT/PATCH/DELETE) with auth, request-ID correlation and history capture.

Transports
  * ``http``       - httpx.Client against ``api_url`` (a running ECS).
  * ``inprocess``  - fastapi TestClient(app.main:app), as the existing ``tests/`` suite does. The runner must
                     set DEMO_MODE / ECS_AUTH_ENABLED / ECS_VALIDATE_CONFIG before the first request.

Identity (see app/auth/middleware.py, app/auth/demo.py)
  * ``demo``   mode: ECS derives identity from the ``role`` / ``user`` pair. They are sent as query params
                     (and merged into form bodies for form posts) exactly like the ECS UI does.
  * ``bearer`` mode: ``Authorization: Bearer <token>`` where the token comes from env ``ECS_FT_TOKEN_<PERSONA>``.

Correlation: every request carries ``X-Request-ID`` (ECS echoes it and stores it in ``audit_log.request_id``).
"""

from __future__ import annotations

import json as _json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

from .config import FunctionalConfig
from .errors import CapabilityBlocked

_REQUEST_ID_HEADERS = ("x-request-id", "x-correlation-id")


@dataclass
class ApiResponse:
    method: str
    url: str
    status: int
    headers: Mapping[str, str]
    content: bytes
    elapsed_ms: float
    request_id: str = ""
    request_summary: dict[str, Any] = field(default_factory=dict)

    # ---- body helpers -----------------------------------------------------------------
    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self) -> Any:
        try:
            return _json.loads(self.content or b"null")
        except ValueError as exc:
            raise AssertionError(f"{self.method} {self.url} did not return JSON (status {self.status}): {self.text[:300]!r}") from exc

    @property
    def is_json(self) -> bool:
        return "json" in (self.headers.get("content-type", "") or "").lower()

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 400

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status < 400

    @property
    def location(self) -> str:
        return self.headers.get("location", "")

    @property
    def notice(self) -> str:
        """The ``notice=`` text ECS puts on redirect URLs (its in-app notification mechanism for form posts)."""
        q = parse_qs(urlparse(self.location).query)
        return (q.get("notice") or [""])[0]

    @property
    def error_message(self) -> str:
        """Error text from ECS JSON error envelopes ({"ok":false,"message"|"error"|"detail"...}) or ''. """
        if not self.is_json:
            return ""
        try:
            body = self.json()
        except AssertionError:
            return ""
        if isinstance(body, dict):
            for key in ("message", "error", "detail", "reason"):
                if body.get(key):
                    return str(body[key])
        return ""

    def to_evidence(self, limit: int = 4000) -> dict[str, Any]:
        return {"method": self.method, "url": self.url, "status": self.status, "request_id": self.request_id,
                "elapsed_ms": round(self.elapsed_ms, 1), "request": self.request_summary,
                "response_snippet": self.text[:limit]}


class EcsApiClient:
    def __init__(self, cfg: FunctionalConfig, *, persona: str | None = None, history: list[dict] | None = None) -> None:
        self.cfg = cfg
        self.persona_key = persona
        self.history: list[dict] = history if history is not None else []
        self._http: Any = None
        self.last: ApiResponse | None = None

    # ---- identity --------------------------------------------------------------------
    def as_persona(self, persona_key: str) -> "EcsApiClient":
        """Return a sibling client acting as another ECS persona (shares request history)."""
        if persona_key not in self.cfg.personas:
            raise CapabilityBlocked(f"Persona '{persona_key}' is not defined in config/test_data.yaml personas "
                                    "(only real ECS roles may be listed).")
        return EcsApiClient(self.cfg, persona=persona_key, history=self.history)

    @property
    def identity(self) -> dict[str, str]:
        p = self.cfg.personas.get(self.persona_key or "", {})
        return {"role": p.get("login_role", ""), "user": p.get("user", "")} if p else {}

    def _auth_headers(self) -> dict[str, str]:
        auth = self.cfg.get("auth", {}) or {}
        if auth.get("mode") == "bearer" and self.persona_key:
            token = self.cfg.secret(f"{auth.get('token_env_prefix', 'ECS_FT_TOKEN_')}{self.persona_key.upper()}")
            if not token:
                raise CapabilityBlocked(
                    f"Bearer auth is enabled but env var {auth.get('token_env_prefix', 'ECS_FT_TOKEN_')}"
                    f"{self.persona_key.upper()} is not set.", requires="persona token")
            return {"Authorization": f"Bearer {token}"}
        return {}

    # ---- transport -------------------------------------------------------------------
    def _client(self):
        if self._http is not None:
            return self._http
        if self.cfg.env.get("transport") == "inprocess":
            from fastapi.testclient import TestClient  # same mechanism as tests/test_*.py
            from app.main import app

            self._http = TestClient(app, follow_redirects=False)
        else:
            import httpx

            self._http = httpx.Client(base_url=self.cfg.api_url, timeout=self.cfg.timeout,
                                      verify=bool(self.cfg.get("verify_tls", True)), follow_redirects=False)
        return self._http

    def close(self) -> None:
        if self._http is not None and hasattr(self._http, "close"):
            self._http.close()
        self._http = None

    # ---- core request ----------------------------------------------------------------
    def request(self, method: str, path: str, *, params: Mapping[str, Any] | None = None,
                json: Any = None, data: Mapping[str, Any] | None = None,
                files: Any = None, headers: Mapping[str, str] | None = None,
                follow_redirects: bool = False, anonymous: bool = False,
                request_id: str | None = None) -> ApiResponse:
        """Send a request. ``anonymous=True`` omits the persona identity (used for unauthenticated probes)."""
        method = method.upper()
        rid = request_id or f"ft-{uuid.uuid4().hex[:16]}"
        q = dict(params or {})
        form = dict(data) if data is not None else None
        hdrs = {"X-Request-ID": rid, **(headers or {})}
        if not anonymous and self.persona_key:
            hdrs.update(self._auth_headers())
            ident = self.identity
            if (self.cfg.get("auth.mode") or "demo") == "demo" and ident:
                if form is not None or files is not None:
                    form = form if form is not None else {}
                    form.setdefault("role", ident["role"])
                    form.setdefault("user", ident["user"])
                q.setdefault("role", ident["role"])
                q.setdefault("user", ident["user"])
        t0 = time.perf_counter()
        client = self._client()
        kwargs: dict[str, Any] = {"params": q, "headers": hdrs}
        if json is not None:
            kwargs["json"] = json
        if form is not None:
            kwargs["data"] = form
        if files is not None:
            kwargs["files"] = files
        raw = client.request(method, path if path.startswith("http") else path, **kwargs)
        hops = 0
        while follow_redirects and raw.status_code in (301, 302, 303, 307, 308) and hops < 5:
            hops += 1
            raw = client.request("GET", raw.headers["location"], headers=hdrs)
        elapsed = (time.perf_counter() - t0) * 1000.0
        resp_rid = next((raw.headers.get(h) for h in _REQUEST_ID_HEADERS if raw.headers.get(h)), "") or rid
        resp = ApiResponse(
            method=method, url=str(getattr(raw, "url", path)), status=raw.status_code,
            headers={k.lower(): v for k, v in raw.headers.items()}, content=raw.content, elapsed_ms=elapsed,
            request_id=resp_rid,
            request_summary={"params": {k: v for k, v in q.items() if k not in ("password", "token")},
                             "json": json, "form_keys": sorted(form) if form else None,
                             "files": [f[0] if isinstance(f, tuple) else f for f in (files or {}).keys()]
                             if isinstance(files, dict) else (len(files) if files else None),
                             "persona": self.persona_key},
        )
        self.last = resp
        self.history.append(resp.to_evidence(limit=800))
        del self.history[:-200]  # bounded
        return resp

    # ---- verbs -----------------------------------------------------------------------
    def get(self, path: str, **kw: Any) -> ApiResponse:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw: Any) -> ApiResponse:
        return self.request("POST", path, **kw)

    def put(self, path: str, **kw: Any) -> ApiResponse:
        return self.request("PUT", path, **kw)

    def patch(self, path: str, **kw: Any) -> ApiResponse:
        return self.request("PATCH", path, **kw)

    def delete(self, path: str, **kw: Any) -> ApiResponse:
        return self.request("DELETE", path, **kw)

    # ---- convenience -----------------------------------------------------------------
    def get_json(self, path: str, **kw: Any) -> Any:
        resp = self.get(path, **kw)
        if resp.status >= 400:
            raise AssertionError(f"GET {path} -> {resp.status}: {resp.text[:300]}")
        return resp.json()

    def login(self) -> ApiResponse:
        """POST /login (ECS login form) as the current persona; returns the redirect response (no token is minted
        by ECS - see app/auth/demo.py - so this only verifies the landing redirect)."""
        ident = self.identity
        return self.post("/login", data={"role": ident.get("role", "")}, anonymous=True)
