# ECS DB Agent — Prototype

> # ⚠️ THIS IS A PROTOTYPE. THIS IS NOT PRODUCTION SECURE.
>
> The DB Agent runs with **no enterprise security enforced**. It is intended for
> **prototype / UAT** use on a **jump server inside a secured internal bank
> network**, where network isolation is the control. Do **not** expose it to an
> untrusted network and do **not** treat it as production-hardened.

A small, self-contained FastAPI micro-service that validates **database** and
**host (SSH)** connectivity from a jump server using **simple configuration
only**. It reuses ECS's existing database connectors for execution and has **no
dependency** on enterprise security infrastructure.

This component is **independent of the ECS platform's own security framework** and
does not modify, weaken, or disable it.

---

## What it deliberately does NOT require

The agent starts and runs using only configuration values. The **absence** of any
of the following **never** prevents it from starting:

- mTLS · TLS certificates · PKI
- JWT authentication · OIDC · OAuth
- HashiCorp Vault / enterprise secret management
- Enterprise SSO · Azure AD · Keycloak
- HSM integration

All of the above are **optional, off-by-default extension points** (see
[Future security](#future-security)).

---

## Configuration

Everything is configurable via environment variables and/or a YAML file. **No
hardcoded IPs or credentials.** Env vars take precedence over YAML; unset values
fall back to safe, non-secret placeholders.

Copy an example and edit the git-ignored copy:

```bash
cp .env.db-agent.example .env.db-agent          # local prototype
cp .env.db-agent.uat.example .env.db-agent.uat  # UAT on the jump server
```

Supported placeholders:

| Group | Variables |
|-------|-----------|
| Database | `DB_HOST` `DB_PORT` `DB_NAME` `DB_USERNAME` `DB_PASSWORD` `DB_SSLMODE` `DB_TIMEOUT_SEC` |
| Host (SSH) | `SSH_HOST` `SSH_PORT` `SSH_USERNAME` `SSH_PASSWORD` `SSH_TIMEOUT_SEC` |
| Agent service | `DB_AGENT_HOST` `DB_AGENT_PORT` |
| Optional YAML | `DB_AGENT_CONFIG` (path; default `config/db_agent.yaml`) |

YAML shape lives in [`config/db_agent.yaml`](../config/db_agent.yaml) (all
placeholders). The agent starts even if every value is blank — unconfigured
targets simply report `configured: false` and connectivity checks degrade
gracefully.

---

## Run

```bash
# Load config (optional) and start
set -a; source .env.db-agent; set +a
python -m db_agent
# or explicitly:
uvicorn db_agent.app:app --host 0.0.0.0 --port 8099
```

Then:

```bash
curl -s localhost:8099/healthz          # {"status":"ok","prototype":true}
curl -s localhost:8099/readyz           # 200 ready OR 503 degraded (informational)
curl -s localhost:8099/config           # resolved config, secrets masked
curl -s localhost:8099/security         # prototype posture, ENABLE_* flags (all off)
curl -s localhost:8099/connectivity     # DB + SSH connectivity summary
curl -s localhost:8099/connectivity/database
curl -s localhost:8099/connectivity/ssh
```

`/readyz` returning **503 (degraded)** is expected before targets are configured
or reachable — it is a **signal, not a startup gate**. The agent keeps serving.

---

## Endpoints

| Method + Path | Purpose |
|---------------|---------|
| `GET /` | Banner + prototype warning |
| `GET /healthz` | Liveness (always 200; no I/O) |
| `GET /readyz` | Readiness (200 when configured targets reachable, else 503) |
| `GET /config` | Resolved config, secrets masked (`SET`/`MISSING`) |
| `GET /security` | Prototype security posture + optional feature flags |
| `GET /connectivity` | DB + SSH connectivity summary |
| `GET /connectivity/database` | DB connectivity (reuses ECS `PostgreSQLConnector`) |
| `GET /connectivity/ssh` | SSH host reachability (TCP probe in the prototype) |

---

## Future security

Security is **optional** and enabled purely through configuration — **no
architecture change** is required. All flags default to `false`:

```dotenv
ENABLE_MTLS=false
ENABLE_JWT=false
ENABLE_VAULT=false
ENABLE_OIDC=false
ENABLE_CERT_AUTH=false
```

The extension points live in [`db_agent/security.py`](security.py) with explicit
`TODO(prod-security)` markers where each integration belongs:

- `tls_context()` — build an `ssl.SSLContext` (server cert/key; mTLS client CA)
  when `ENABLE_MTLS` / `ENABLE_CERT_AUTH` is set.
- `authenticate_request()` — validate JWT/OIDC bearer tokens when `ENABLE_JWT` /
  `ENABLE_OIDC` is set (the auth middleware in `db_agent/app.py` already calls it).
- `resolve_secret()` — fetch from Vault / enterprise secret manager when
  `ENABLE_VAULT` is set.

### Production hardening checklist (before any production deployment)

- [ ] Enable **TLS/mTLS** (`ENABLE_MTLS`) with real certificates.
- [ ] Enable **JWT/OIDC** authentication (`ENABLE_JWT` / `ENABLE_OIDC`).
- [ ] Enable **Vault / enterprise secret management** (`ENABLE_VAULT`) — no
      plaintext credentials in env/YAML.
- [ ] Enable **certificate authentication** (`ENABLE_CERT_AUTH`).
- [ ] Integrate **centralized identity** (SSO / Azure AD / Keycloak).
- [ ] Add **audit logging enhancements** for every connectivity/query action.
- [ ] Restrict network exposure; least-privilege, read-only DB accounts.

---

## Relationship to ECS

The DB Agent **reuses** ECS's existing database connector
(`modules/operations/engines/postgresql_connector.py`) for real DB checks and
falls back to a TCP probe if the driver is unavailable. It adds **no** new
connector logic and touches **none** of the ECS platform's security framework,
auth, RBAC, or configuration. It is a standalone prototype process.
