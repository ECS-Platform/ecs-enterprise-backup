# Phase 2 — DEMO_MODE Validation

Tested live against http://127.0.0.1:8000 with **no Authorization header, no token, no JWT, no Azure AD**.

Result: **all 66 navigation routes load (HTTP 200), zero 401/403, zero unauthorized.**

401/403 occurrences: 0

| Route family | Routes | All HTTP 200 | 401/403 | Token required |
|---|---|---|---|---|
| /dashboard | 5 | Yes | 0 | No |
| /mvp/* | 56 | Yes | 0 | No |
| /framework/* | 5 | Yes | 0 | No |
| operations / governance / evidence (/mvp/platform/*) | 11 | Yes | 0 | No |
| /ai-sdlc/* | 11 | Yes | 0 | No |
| /mvp/roi (ROI) | 1 | Yes | 0 | No |

## Bypass mechanism

- `DEMO_MODE=true` -> `app/auth/demo.py:demo_mode()` returns True.
- `app/auth/middleware.py`: authentication bypassed for every route.
- `app/auth/page_guard.py` + `app/auth/enforcement.py`: page guard & RBAC enforcement disabled.
- No Azure AD / OIDC / JWT / Authorization header needed for any page.

Sample probed without headers: /dashboard, /mvp/roi, /framework/PCI-DSS, /mvp/platform/scorecard, /mvp/ai-sdlc/requirements -> all 200.
