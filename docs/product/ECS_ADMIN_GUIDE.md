# ECS Administrator Guide (Knowledge Transfer)

**Audience:** platform administrators, solution architects. **Goal:** configure, secure, and administer ECS. Grounded in `config/*.yaml`, `app/`, `ecs_platform/`, `docker-compose.yml`.

---

## 1. Master switches

| Variable | Default | Effect |
|---|---|---|
| `ECS_AUTH_ENABLED` | `true` (secure) | Enables OIDC/JWT + RBAC enforcement |
| `DEMO_MODE` | `false` | Serves deterministic synthetic data; relaxes external dependencies |

Demo: `DEMO_MODE=true ECS_AUTH_ENABLED=false`. Production: both at secure defaults with real IdP + DB.

## 2. Configuration files (`config/`)

| File | Governs |
|---|---|
| `auth.yaml` | OIDC issuer/audience, JWT, demo bypass |
| `rbac.yaml` | **Canonical** RBAC: 9 roles, permissions, scopes (`rbac_catalog`) |
| `repository.yaml` | Postgres evidence repository connection |
| `vectorstore.yaml` | pgvector store for RAG |
| `llm.yaml` | LLM provider (Ollama/Gemini/OpenAI/Azure/Claude) |
| `integrations.yaml` | 12 connectors: enable flags, URLs, credentials (`${ENV}`) |
| `roi.yaml` | ROI rates/assumptions |

All values support `${VAR}` / `${VAR:-default}` resolution (`ecs_platform/config/loader.py`). `.env` is loaded at startup (`app/env_bootstrap.py`).

## 3. RBAC administration

- **Canonical system:** `config/rbac.yaml` → `rbac_catalog` (9 roles, scope dimensions, `can_*` predicates). This is the source of truth.
- **Legacy system:** `role_permissions.py` still present; normalized for compatibility (see `docs/developer-manual/ECS_RBAC_LEGACY_FLAWS.md`). **Do not add new rules to the legacy path.**
- Enforcement: `page_guard` (page access) + `mutation_guard` (write actions), active only when `ECS_AUTH_ENABLED=true`.
- Add a role: edit `rbac.yaml` → define permissions + scope → restart. No code change for standard roles.

## 4. Onboarding a framework (admin)

1. `/mvp/framework-loader` → upload control library.
2. `/mvp/framework-admin` → run onboarding wizard → activate.
3. Verify coverage scan + reuse mappings. (No code change — catalog-driven.)

## 5. Onboarding a connector (admin)

Per `demo-data/SAAS_CONNECTOR_READINESS.md`:
1. Create credential in source system.
2. Add env vars to host `.env` (never commit secrets).
3. Set `ECS_<CONNECTOR>_ENABLED=true`.
4. `docker compose up -d ecs` (re-reads env; no rebuild).
5. Verify in **Integration Health** → `Connected`; click **Sync Now**.

All 12 connectors are **interface-complete and disabled by default** — one flag away from live.

## 6. Deployment (Docker Compose — 10 services)

`ecs` (app) + Postgres + pgvector + MinIO + Redis + optional source/demo-connector profiles (`sources`, `demo-connectors`). Bring up: `docker compose up -d`. Health: `GET /healthz`, `/readyz`, `/api/platform/health`.

## 7. Security checklist

- [ ] `ECS_AUTH_ENABLED=true` in production.
- [ ] Real OIDC issuer/audience in `auth.yaml`.
- [ ] Secrets via host `.env` / vault — never in YAML or git.
- [ ] Postgres credentials rotated; repository reachable.
- [ ] Confirm page/mutation guards active (try a 403).

## 8. Backup & recovery

See `docs/operations/RECOVERY_RUNBOOK.md` — Postgres evidence repository backup/restore/migration (authoritative).

## 9. Admin screens

`/mvp/integration-health`, `/mvp/integrations-hub`, `/mvp/platform/inventory`, `/mvp/platform/onboarding`, `/mvp/cmdb`, `/mvp/governance-quality`, `/mvp/framework-admin`.

## 10. Common admin tasks → commands

See `docs/00-start-here/COMMON_COMMANDS.md` (start/stop/test/seed/backup/reset). Tests: `./venv/bin/pytest` (39 suites).
