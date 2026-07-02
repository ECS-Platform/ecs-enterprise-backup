# ECS Local / Demo Authentication Fix

**Branch:** `cursor/predefined-queries-module`
**Change type:** Minimal, additive, opt-in. Authentication middleware + env template only.
**Purpose:** Make ECS reachable through a normal browser after `/login` on a local/demo host, **without weakening or removing production Azure AD / OIDC authentication.**

---

## 1. Root cause

The local browser login flow fails with **401 Unauthorized** after `/login` because ECS uses **token-based (Bearer JWT) authentication**, but `/login` never issues a token or session cookie:

1. `config/auth.yaml` sets `auth.enabled = ${ECS_AUTH_ENABLED:-true}` and `auth.provider = ${ECS_AUTH_PROVIDER:-azure_ad}`. With `.env` `ECS_AUTH_ENABLED=true`, authentication is **ON** and the active provider is **Azure AD**.
2. The Azure AD provider (`app/auth/providers.py::AzureADProvider`) authenticates by reading an `Authorization: Bearer <JWT>` header (`_bearer_token`). It is designed for an SPA/API client that attaches a validated token — there is no server-side session.
3. The `/login` route (`app/main.py`) only performs a **server-side redirect** (`RedirectResponse` → `/dashboard?role=...&user=...`). It does **not** validate credentials, mint a JWT, or set any cookie.
4. Therefore the browser's follow-up `GET /dashboard` carries **no `Authorization` header and no session cookie**. `AuthenticationMiddleware` (`app/auth/middleware.py`) routes it to the Azure AD provider, which raises `missing_token`, and the middleware returns **401** (`Token validation failure: missing_token` / `Login failure: missing_token via azure_ad`).

This is correct, secure behaviour for production (the client is expected to present a Bearer token). It simply makes the app unusable through a plain browser on a local/demo host unless a bypass is enabled.

**Existing bypasses before this fix:**
- `DEMO_MODE=true` — full pass-through (auth + RBAC + page guards). Works, but is the "big red switch" for executive demos and also disables RBAC.
- `ECS_AUTH_DEV_MODE=true` — forces a static `dev-user`/`admin` principal (ignores the login-selected role).

There was **no narrow, clearly-named "let me log in locally" switch** that keeps `ECS_AUTH_ENABLED=true` while allowing browser login and reflecting the chosen role — which is what this fix adds.

---

## 2. Fix

Introduce an explicit, opt-in, **local/dev-only** authentication bypass flag: **`ECS_LOCAL_AUTH_BYPASS`**.

- When `DEMO_MODE=true` **or** `ECS_LOCAL_AUTH_BYPASS=true`, the authentication middleware short-circuits (transparent pass-through) so no Bearer token is required and the browser `/login` → `/dashboard` flow returns 200.
- `DEMO_MODE` keeps its original behaviour exactly (anonymous pass-through, `principal=None`, plus RBAC/page-guard bypass elsewhere).
- `ECS_LOCAL_AUTH_BYPASS` bypasses **authentication only** (it does not touch RBAC flags) and additionally synthesises a lightweight principal from the `?role=&user=` query params so the identity selected at login flows to downstream code.
- With **both flags off** (the production default), nothing changes: Azure AD / OIDC / JWT authentication is enforced exactly as before.

### Why middleware-level (not a fake cookie/JWT)
A cookie/session login would require minting and validating a server-side session or a self-signed JWT — new surface area and a larger change. The middleware already had a proven, isolated bypass path for `DEMO_MODE`; extending it with a second explicitly-named local flag is the smallest, safest change and reuses the already-validated pass-through.

---

## 3. Files changed

| File | Change |
|---|---|
| `app/auth/demo.py` | Added `local_auth_bypass()` (reads `ECS_LOCAL_AUTH_BYPASS`), a generic `_flag()` helper, and `auth_bypassed()` (True when `DEMO_MODE` **or** `ECS_LOCAL_AUTH_BYPASS` is on). `demo_mode()` behaviour unchanged. Expanded module docstring. |
| `app/auth/middleware.py` | Bypass branch now checks `auth_bypassed()` instead of `demo_mode()`. Added `_demo_principal_from_request()` to synthesise a local principal from `?role=&user=` for the `ECS_LOCAL_AUTH_BYPASS` path (DEMO_MODE still uses `principal=None`). No change to the token-provider path. |
| `.env.example` | Documented the new `ECS_LOCAL_AUTH_BYPASS=false` flag (local/dev only) next to `DEMO_MODE`. |
| `docs/LOCAL_AUTH_DEMO_FIX.md` | This document. |

No routes, services, engines, RBAC code, JWT/JWKS validation, provider registry, benchmark files, or AI SDLC module files were modified.

---

## 4. Local behaviour (how to run the demo)

The repository `.env` is **git-ignored**; it was **not** modified by this change. To run locally with browser login, set in your local `.env` (or export before starting):

```bash
# Keep production auth code active, but allow local browser login:
ECS_AUTH_ENABLED=true
ECS_LOCAL_AUTH_BYPASS=true      # local/dev ONLY — never in production
DEMO_MODE=false                 # (optional) leave off; ECS_LOCAL_AUTH_BYPASS is enough
```

Then:

```bash
./start_ecs.sh                  # or: uvicorn app.main:app --reload
```

- `POST /login` (role=owner) → 303 redirect → `GET /dashboard?role=owner&user=AppOwner` → **200**.
- AI SDLC navigation and pages (`/mvp/ai-sdlc`, `/mvp/ai-sdlc/control-tower`, …) → **200**.
- `/healthz` → 200; `/readyz` → 200 when PostgreSQL is reachable, else 503 (unchanged; DB-dependent, not auth-dependent).

Alternative full-demo switch (also disables RBAC/page guards): `DEMO_MODE=true`.

---

## 5. Production auth safety

- **Nothing is removed or weakened.** Azure AD / OIDC / JWT validation, the provider registry, JWKS handling, and public-path config are all untouched.
- The bypass is **default OFF** and only activates when an operator explicitly sets `ECS_LOCAL_AUTH_BYPASS=true` or `DEMO_MODE=true`.
- Verified: with `ECS_AUTH_ENABLED=true` and both flags off, `GET /dashboard` returns **401 `missing_token`** — identical to the original production behaviour.
- The synthesised local principal is created **only** inside the bypass branch (gated on the flags) and is labelled `auth_source="local_bypass"`; it can never be produced when auth is enforced.
- Recommendation: never set `ECS_LOCAL_AUTH_BYPASS` / `DEMO_MODE` on a production/internet-exposed host; keep them out of production `.env` and deployment manifests.

---

## 6. Validation

```bash
# 1) Syntax / compile
python -m compileall app modules scripts        # -> exit 0 (clean)
```

Behavioural checks (TestClient, one subprocess per scenario so config cache does not leak):

| Scenario | Env | `GET /dashboard` | `GET /healthz` | Result |
|---|---|---|---|---|
| Production | `ECS_AUTH_ENABLED=true`, both flags off | **401** (`missing_token`) | 200 | auth enforced ✔ |
| Local bypass | `ECS_LOCAL_AUTH_BYPASS=true`, `ECS_AUTH_ENABLED=true` | **200** | 200 | browser login works ✔ |
| Demo mode | `DEMO_MODE=true` | **200** | 200 | full pass-through ✔ |

Live-server curl (started with `ECS_AUTH_ENABLED=true ECS_LOCAL_AUTH_BYPASS=true`):

```bash
curl -i http://127.0.0.1:8000/                                   # 200
curl -i http://127.0.0.1:8000/healthz                            # 200 {"status":"ok"}
curl -i "http://127.0.0.1:8000/readyz"                           # 503 (no local DB; route reachable, not 401)
curl -i "http://127.0.0.1:8000/dashboard?role=owner&user=AppOwner"   # 200

# Cookie-jar login flow (mirrors the browser):
curl -i -c /tmp/ecs_cookies.txt -d "role=owner&user=AppOwner" -X POST http://127.0.0.1:8000/login
#   -> 303 See Other; location: /dashboard?role=owner&user=AppOwner
curl -i -b /tmp/ecs_cookies.txt "http://127.0.0.1:8000/dashboard?role=owner&user=AppOwner"   # 200

# AI SDLC reachable:
curl -so /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/mvp/ai-sdlc?role=owner&user=AppOwner"                # 200
curl -so /dev/null -w "%{http_code}\n" "http://127.0.0.1:8000/mvp/ai-sdlc/control-tower?role=owner&user=AppOwner"  # 200
```

Production-simulation live-server curl (both flags off): `GET /dashboard` → **401** `missing_token`, `GET /healthz` → 200.

> Note on `/login` + curl: `/login` performs a redirect and does not itself set an ECS session cookie (no cookie is required in bypass mode). The cookie jar in the commands above simply follows the redirect target; the dashboard loads because the bypass is active, exactly as it will for a real browser.

> Validation used a throwaway virtualenv at `/tmp` with the app's already-declared demo deps (`fastapi`, `uvicorn`, `jinja2`, …). No new dependency was added to the repo and the system Python was not modified.

---

## 7. Expected result

- Local/demo host with `ECS_LOCAL_AUTH_BYPASS=true`: log in as any role → dashboards and AI SDLC pages load (HTTP 200); `/healthz` and `/readyz` behave as before.
- Production (both flags off): unchanged — token-based Azure AD / OIDC authentication is enforced; unauthenticated `/dashboard` returns 401.

---

## 8. Confirmations

- **Benchmark files untouched:** `scripts/run_neev_validation_benchmark.py`, `scripts/run_16k_1k_token_validation.py`, `benchmarks/ai_workload/*`, `docs/benchmarks/*` — not modified.
- **AI SDLC module untouched:** no files under `modules/ai_sdlc/` were changed by this fix.
- **Production auth not disabled:** Azure AD / OIDC / JWT code preserved; bypass is opt-in and default OFF.
