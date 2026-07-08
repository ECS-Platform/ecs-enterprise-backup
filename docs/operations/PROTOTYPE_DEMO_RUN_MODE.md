# ECS Prototype / Demo Run Mode

Run ECS for a **prototype, demo, or budget-approval walkthrough** without a live
Identity Provider, Vault, TLS certificates, key rotation, real connector
credentials, or production databases — while keeping every security layer in the
codebase intact for later UAT / PROD hardening.

> **Nothing is removed.** JWT/OIDC, RBAC, TLS, Vault/secrets, security headers,
> and config validation all remain. Demo mode only makes their *enforcement*
> **non-blocking by default**. Production and DR stay strict.

---

## 1. Why demo mode exists

The browser `/login` flow issues a server-side redirect and does **not** mint a
JWT/session cookie (the Azure AD / OIDC providers expect a SPA to attach a Bearer
token). With strict auth on, an ordinary browser hitting `/dashboard` carries no
credential and is rejected with `missing_token` (401). Likewise, strict config
validation, required secrets, and required infrastructure would otherwise block a
laptop/prototype run. Demo mode provides a safe, explicit escape hatch so ECS
runs end-to-end for evaluation **without weakening production**.

---

## 2. How to run without tokens / certs / vault / OIDC

The single switch is the **security mode**. Either set `ECS_SECURITY_MODE=demo`
or the long-standing `DEMO_MODE=true` (both resolve to demo mode):

```bash
# From the repo root
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start in prototype/demo mode (no tokens, certs, vault, OIDC, secrets, DB, LLM)
DEMO_MODE=true uvicorn app.main:app --host 127.0.0.1 --port 8000
# or, equivalently:
ECS_SECURITY_MODE=demo uvicorn app.main:app --port 8000
```

Then open `http://127.0.0.1:8000/dashboard?role=owner&user=Demo`.

- `GET /healthz` → `200` (liveness; does no I/O).
- `GET /readyz` → `503` **degraded is expected** without PostgreSQL — this never
  blocks startup; the app keeps serving demo/in-memory data.

Exact `.env` values are in [§6](#6-exact-env-values-for-prototype-mode). The
canonical flags and their demo defaults live in `.env.example` (the
"SECURITY MODE" block at the top).

---

## 3. Which security layers are bypassed (demo mode)

| Layer | Demo behavior | Flag (explicit override) |
|-------|---------------|--------------------------|
| Authentication (JWT/OIDC) | Pass-through (no token needed) | `ECS_AUTH_ENABLED` (default off in demo) |
| RBAC enforcement | Disabled (role from `?role=`) | `ECS_RBAC_ENFORCEMENT` (forced off in demo) |
| OIDC / IdP requirement | Not required | `ECS_REQUIRE_OIDC` (default off) |
| TLS / HTTPS | Not required | `ECS_REQUIRE_TLS` (default off) |
| Vault / secrets manager | Not required | `ECS_REQUIRE_VAULT` (default off) |
| Real secrets present | Missing → **warn**, not fail | `ECS_REQUIRE_SECRETS` (default off) |
| Config validation errors | **Warn**, do not abort startup | `ECS_STARTUP_FAIL_ON_CONFIG_ERROR` (default off) |
| PostgreSQL / Redis / vector / LLM | In-memory / deterministic fallback | `ECS_ALLOW_IN_MEMORY` (default on) |
| Live connector execution | **Always opt-in / OFF** | `ECS_CONNECTOR_EXECUTION_ENABLED` |
| Security headers | **Remain ON** (safe defaults) | (always on; HSTS only over HTTPS) |

Security headers stay enabled even in demo — they cost nothing and are good
hygiene; HSTS is emitted only over HTTPS and CSP is opt-in via `ECS_CSP`.

---

## 4. Which security code remains available (unchanged)

All of it. Demo mode changes no production default and deletes nothing:

- `app/auth/*` — Azure AD / OIDC providers, JWT validation, middleware, RBAC
  (`roles`, `authz`, `enforcement`, `scope`, `page_guard`, `mutation_guard`).
- `config/config_validation.py` — full environment-aware validator.
- `app/security_mode.py` — the central resolver (this feature); it only supplies
  mode-aware **defaults** and honors every explicit flag.
- Security-headers middleware, request-ID middleware, audit trail, evidence
  hashing — all active.

Turn strict behavior back on at any time by setting the flags (see [§7](#7-how-to-switch-later-to-uat--prod-security)).

---

## 5. Difference between LOCAL, UAT, PROD, DR

`ECS_SECURITY_MODE` resolves to one of `demo | uat | production`. When unset it
is derived from `ECS_ENV` (`local`/`dev` → demo, `sit`/`uat` → uat, `prod`/`dr`
→ production), so existing deployments keep their behavior.

| Aspect | demo (LOCAL) | uat | production (PROD/DR) |
|--------|--------------|-----|---------------------|
| Authentication | off | on | on |
| RBAC enforcement | off | off (opt-in) | on |
| Require TLS / secrets / OIDC | no | no (opt-in) | yes |
| In-memory fallback allowed | yes | yes | no |
| Config errors abort startup | no | no (unless strict) | yes |
| localhost/loopback for remote endpoints | allowed | rejected | rejected |
| Live connector execution | opt-in | opt-in | opt-in |

UAT is deliberately **planning-tolerant**: it enables auth but allows placeholder
configs and missing secrets so teams can stand up an environment before all
credentials exist. Flip on `ECS_STRICT_CONFIG_VALIDATION` +
`ECS_REQUIRE_SECRETS` + `ECS_STARTUP_FAIL_ON_CONFIG_ERROR` for a hardened UAT
dress rehearsal. PROD/DR are strict and never silently relaxed.

---

## 6. Exact `.env` values for prototype mode

```dotenv
ECS_SECURITY_MODE=demo
ECS_AUTH_ENABLED=false
ECS_RBAC_ENFORCEMENT=false
ECS_REQUIRE_TLS=false
ECS_REQUIRE_VAULT=false
ECS_REQUIRE_SECRETS=false
ECS_REQUIRE_OIDC=false
ECS_ALLOW_DEMO_AUTH=true
ECS_ALLOW_IN_MEMORY=true
ECS_STRICT_CONFIG_VALIDATION=false
ECS_STARTUP_FAIL_ON_CONFIG_ERROR=false
ECS_CONNECTOR_EXECUTION_ENABLED=false
```

Shortcut: setting just `DEMO_MODE=true` (or `ECS_SECURITY_MODE=demo`) yields the
same non-blocking posture — every flag above is the demo default.

---

## 7. How to switch later to UAT / PROD security

No code change — only environment values (see `.env.uat.example`,
`.env.prod.example`, `.env.dr.example`):

```bash
# UAT (planning-tolerant)
ECS_ENV=uat ECS_SECURITY_MODE=uat ECS_AUTH_ENABLED=true uvicorn app.main:app

# Hardened UAT dress rehearsal
ECS_ENV=uat ECS_SECURITY_MODE=uat ECS_AUTH_ENABLED=true \
  ECS_REQUIRE_SECRETS=true ECS_STRICT_CONFIG_VALIDATION=true \
  ECS_STARTUP_FAIL_ON_CONFIG_ERROR=true uvicorn app.main:app

# Production (strict by default)
ECS_ENV=prod ECS_SECURITY_MODE=production uvicorn app.main:app
# Validate config + secrets before deploy:
ECS_ENV=prod ECS_VALIDATE_SECRETS=1 python -m config.config_validation prod --check-secrets
```

To enable **live** connector collection in any environment (requires real
credentials, still opt-in): `ECS_CONNECTOR_EXECUTION_ENABLED=true`.

---

## 8. Troubleshooting startup blockers

| Symptom | Cause | Fix (prototype) |
|---------|-------|-----------------|
| Startup aborts: "configuration is invalid" | Strict env or forced validation with config errors | `ECS_STARTUP_FAIL_ON_CONFIG_ERROR=false` (or `ECS_VALIDATE_CONFIG=off`, or `ECS_SECURITY_MODE=demo`) |
| `/dashboard` returns 401 `missing_token` | Auth is on but the browser has no Bearer token | `DEMO_MODE=true` (or `ECS_AUTH_ENABLED=false`, or `ECS_LOCAL_AUTH_BYPASS=true`) |
| `/readyz` returns 503 | PostgreSQL not reachable | Expected in demo — in-memory fallback is used; not a blocker |
| Connector "collect" does nothing | Live execution is opt-in | Set `ECS_CONNECTOR_EXECUTION_ENABLED=true` **and** configure the adapter |
| Config validation shows secret warnings | Real secrets absent | Ignore in demo; set `ECS_REQUIRE_SECRETS=true` + `ECS_VALIDATE_SECRETS=1` to enforce |
| RBAC blocks a page | RBAC enforcement on | `ECS_SECURITY_MODE=demo` (demo forces RBAC off) |

Inspect the resolved posture in the startup logs — ECS logs a
`Security mode: demo (auth=..., rbac=..., ...)` line at boot.

---

## Related docs

- `.env.example` — canonical flags (SECURITY MODE block)
- `docs/00-start-here/DEMO_MODE_SETUP.md` — demo quickstart
- `docs/operations/environment-configuration/00_ENVIRONMENT_CONFIGURATION_GUIDE.md` — full env framework
- `docs/operations/UAT_VALIDATION_RUNBOOK.md` — UAT validation
