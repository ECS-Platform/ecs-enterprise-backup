"""Dashboard / page authorization guard (Phase 2, Step 2C).

Eliminates direct-URL bypass of persona dashboards. A guarded page route asks this
helper whether the authenticated principal's role may view the page; if not, the
caller returns the denial response directly:
  * browser routes: a lightweight HTTP 403 "Access Denied" HTML page
  * JSON/API routes: HTTP 403 with a structured body

SCOPE — page/dashboard access only:
  * No scope filtering, no GET data filtering, no mutation/API redesign.
  * Only explicitly-wired page routes call guard_page().

Gated by RBAC_PAGE_ENFORCEMENT_ENABLED (default FALSE):
  * OFF -> guard_page() returns None (allow); existing ECS behavior/UX unchanged.
  * ON  -> the effective role is derived from the authenticated principal (Step 2B
           foundation) and checked against the canonical page catalog via PolicyEngine.

A page route may declare ONE page key or SEVERAL acceptable keys (any-of), which is
how shared landing pages (e.g. compliance + security view the same screen) are
expressed without changing the RBAC catalog.

Best-effort and fail-safe-to-allow: any internal error returns None (allow), so a
guard fault can never harden into an outage.
"""

from __future__ import annotations

import os
from html import escape
from typing import Any, Iterable
from urllib.parse import quote

from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse


def page_enforcement_enabled() -> bool:
    """Feature flag. Default FALSE: no page is gated (legacy behavior).

    Global DEMO_MODE forces this OFF so every navigable page loads token-free.
    """
    try:
        from app.auth.demo import demo_mode
        if demo_mode():
            return False
    except Exception:  # noqa: BLE001 - never let the demo check harden into a guard
        pass
    return str(os.environ.get("RBAC_PAGE_ENFORCEMENT_ENABLED", "")).strip().lower() in {
        "1", "true", "yes", "on",
    }


def _as_pages(pages: str | Iterable[str]) -> list[str]:
    if isinstance(pages, str):
        return [pages]
    return [str(p) for p in pages if p]


def can_view_page(request: Any, pages: str | Iterable[str], fallback_role: str = "") -> bool:
    """Return whether the current request may view ANY of `pages`.

    Always True when the flag is off. When on, derives the canonical role from the
    principal (Step 2B) and consults the PolicyEngine page catalog. Never raises."""
    if not page_enforcement_enabled():
        return True
    keys = _as_pages(pages)
    try:
        from app.auth.enforcement import canonical_effective_role
        from app.auth.authz import get_policy_engine

        role = canonical_effective_role(request, fallback_role)
        engine = get_policy_engine()
        return any(engine.can_view_page(role, p) for p in keys)
    except Exception:  # noqa: BLE001 - fail safe to allow (additive hardening)
        return True


def _denied_role(request: Any, fallback_role: str) -> str:
    try:
        from app.auth.enforcement import canonical_effective_role

        return canonical_effective_role(request, fallback_role) or fallback_role or "unknown"
    except Exception:  # noqa: BLE001
        return fallback_role or "unknown"


_ACCESS_DENIED_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Access Denied — ECS</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
   background:#0f172a;color:#e2e8f0;margin:0;display:flex;min-height:100vh;
   align-items:center;justify-content:center}}
 .card{{background:#1e293b;border:1px solid #334155;border-radius:12px;
   padding:36px 40px;max-width:520px;width:90%;box-shadow:0 10px 40px rgba(0,0,0,.4)}}
 h1{{margin:0 0 6px;font-size:22px;color:#f87171}}
 .sub{{color:#94a3b8;font-size:13px;margin-bottom:20px}}
 dl{{margin:0;display:grid;grid-template-columns:130px 1fr;gap:8px 14px;font-size:14px}}
 dt{{color:#94a3b8}} dd{{margin:0;color:#e2e8f0;word-break:break-word}}
 .actions{{margin-top:24px}}
 a{{display:inline-block;background:#2563eb;color:#fff;text-decoration:none;
   padding:9px 16px;border-radius:8px;font-size:14px}}
</style></head>
<body><div class="card">
 <h1>403 — Access Denied</h1>
 <div class="sub">You are authenticated, but your role is not permitted to view this page.</div>
 <dl>
   <dt>User</dt><dd>{user}</dd>
   <dt>Role</dt><dd>{role}</dd>
   <dt>Requested page</dt><dd>{page}</dd>
   <dt>Reason</dt><dd>{reason}</dd>
 </dl>
 <div class="actions"><a href="{home}">Return to your dashboard</a></div>
</div></body></html>"""


def _access_denied_html(*, user: str, role: str, page: str, reason: str, home: str) -> str:
    return _ACCESS_DENIED_HTML.format(
        user=escape(user or "unknown"), role=escape(role or "unknown"),
        page=escape(page or "unknown"), reason=escape(reason), home=escape(home))


def guard_page(request: Any, pages: str | Iterable[str], *, fallback_role: str = "",
               response: str = "html", user: str = "", home: str = "/",
               page_label: str = "") -> Any | None:
    """Authorize a page view. Returns None to allow, or a 403 denial response.

    Parameters:
      pages        - one page key or several acceptable keys (any-of).
      fallback_role- caller-supplied role used when the flag is off / no principal.
      response     - 'html' (browser) -> 403 HTML page; 'json' (API) -> 403 JSON;
                     'redirect' -> 303 to the access-denied page.
      user         - shown on the access-denied page.
      home         - "return to dashboard" link target.
      page_label   - human label for the requested page (defaults to first key).

    When the flag is off this returns None immediately (no behavior change)."""
    if not page_enforcement_enabled():
        return None
    if can_view_page(request, pages, fallback_role):
        return None

    keys = _as_pages(pages)
    label = page_label or (keys[0] if keys else "page")
    role = _denied_role(request, fallback_role)
    reason = f"Role '{role}' is not authorized for '{label}'."

    if response == "json":
        return JSONResponse(
            {"ok": False, "error": "forbidden", "reason": "page_not_authorized",
             "page": label, "role": role, "detail": reason},
            status_code=403,
        )
    if response == "redirect":
        sep = "&" if "?" in home else "?"
        url = (f"/access-denied?page={quote(label)}&role={quote(role)}"
               f"&user={quote(user)}&home={quote(home)}")
        return RedirectResponse(url=url, status_code=303)
    return HTMLResponse(
        _access_denied_html(user=user, role=role, page=label, reason=reason, home=home),
        status_code=403,
    )
