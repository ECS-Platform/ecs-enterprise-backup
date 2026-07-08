# ECS — Demo Mode Setup

How ECS runs as a **self-contained demo**: no Azure AD, no JWT, no RBAC enforcement, no database, no LLM. Everything here is derived from `app/auth/demo.py`, `app/env_bootstrap.py`, `app/main.py`, `config/*.yaml`, `docker-compose.yml`, and the `demo-data/` seed scripts.

> See also the original incident writeup `docs/00-start-here/ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md`. **This document supersedes its env-loading guidance:** the current build *does* load `.env` automatically via `app/env_bootstrap.py`, so you no longer have to `export` flags in the same shell (though that still works).

> **Prototype / budget-approval run mode:** for the full set of configurable
> security gates (auth, RBAC, TLS, Vault, OIDC, secrets, config validation) and
> how to run with **none of them blocking** while keeping the code intact for
> UAT/PROD, see [`docs/operations/PROTOTYPE_DEMO_RUN_MODE.md`](../operations/PROTOTYPE_DEMO_RUN_MODE.md).
> The canonical flags are resolved centrally by `app/security_mode.py` and
> documented in the "SECURITY MODE" block at the top of `.env.example`.

---

## 1. What "demo mode" actually does

There is a **single master switch**, `DEMO_MODE` (`app/auth/demo.py::demo_mode()`), read from the environment at call time. When `true` it short-circuits **all** access enforcement:

| Layer | Normal behaviour | With `DEMO_MODE=true` |
|---|---|---|
| Authentication middleware (`app/auth/middleware.py`) | Validates Azure AD / OIDC / JWT on non-public paths | Transparent pass-through — no token required |
| RBAC enforcement (`app/auth/enforcement.py`) | Capability/permission decisions | Disabled (legacy allow-all) |
| Page / dashboard guards (`app/auth/page_guard.py`) | 403 for unauthorized personas | Disabled — every left-nav route loads |

It **removes no code and changes no production behaviour** — it only bypasses enforcement while on. Default is OFF (absent/blank/unknown → secure). Use only on an isolated, non-production host.

`ECS_AUTH_ENABLED=false` is the complementary flag: it tells the auth config the master switch is off so the middleware installs in pass-through mode. For a clean demo, set **both**.

---

## 2. What is mocked / synthetic / bypassed

| Aspect | In demo mode |
|---|---|
| **Authentication** | Bypassed — no IdP, no token. (`DEMO_MODE` / `ECS_AUTH_ENABLED=false`.) |
| **RBAC & page guards** | Bypassed — all personas/pages reachable. |
| **Showcase data** | **Synthetic & deterministic.** `seed_demo_workflow_state()` (`modules/executive_overview/engines/demo_seed.py`) runs at startup; dashboards, the 15-framework catalog, controls, evidence, ROI (`config/roi.yaml`), and metrics are generated in-memory. |
| **Database (PostgreSQL)** | **Not required.** `init_repository()` is best-effort; `/readyz` returns 503 but the UI serves fully. |
| **LLM / RAG** | **Optional.** With no provider reachable the assistant uses a deterministic fallback (logged `LLM-RAG disabled … deterministic fallback`). |
| **Connectors** | **Not required** for the showcase. The connector-driven evidence flow (Gitea/Jenkins/SonarQube) is a *separate, optional* Docker activity (§6). |
| **Evidence intelligence engines** | All default OFF (sufficiency, lineage, reuse, timeline, etc.); enable individually to demo them. |

So there are **two distinct "demos"**:
- **A. Showcase demo (native, zero deps):** synthetic in-memory data, no Docker. Use this for UI/persona/framework/ROI walkthroughs.
- **B. Connector demo (Docker stack):** real Gitea/Jenkins/SonarQube seeded with 6 banking apps, producing real correlated evidence. Use this to demonstrate live evidence collection.

---

## 3. Running ECS in Demo Mode (A — native showcase)

### Required files
- `.env` at repo root containing at least:
  ```bash
  DEMO_MODE=true
  ECS_AUTH_ENABLED=false
  ```
- The repository source (no DB, no Docker, no Node).

### Optional files
- The rest of `.env` (copy from `.env.example`) — every other value can stay default.
- `config/*.yaml` — defaults are fine; no edits needed for the showcase.

### Exact commands
```bash
cd ECS
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DEMO_MODE=true and ECS_AUTH_ENABLED=false

uvicorn app.main:app --reload
```

Alternative (no `.env`) — export in the **same** shell that runs uvicorn (`override=False` means real env wins):
```bash
export DEMO_MODE=true ECS_AUTH_ENABLED=false
uvicorn app.main:app --reload
```

### Expected behaviour
Startup banner confirms the mode:
```
[ECSStartup] DEMO_MODE=true
[ECSStartup] ECS_AUTH_ENABLED=false
[ECSStartup] .env loaded=True via python-dotenv
[ECSPlatform] Evidence repository unavailable: ...        # expected (no DB)
[ECSPlatform] LLM-RAG disabled: provider not configured   # expected (no LLM)
... platform ready on 127.0.0.1:8000
```
- `http://127.0.0.1:8000/` loads the role chooser; every persona dashboard opens without a token.
- `GET /healthz` → `{"status":"ok"}`.

### Known limitations (mode A)
- `/readyz` returns **503** (no Postgres) — expected; use `/healthz` for liveness.
- No durable persistence: durable audit (`AUDIT_WORKFLOW_ENABLED`) and durable observations (`OBSERVATIONS_DURABLE_ENABLED`) are no-ops without Postgres.
- `/api/platform/health` shows no connector evidence (use mode B for that).
- The AI assistant answers from the deterministic fallback, not live RAG, unless you configure a provider.
- Demo state is regenerated each startup — it is **not** a record of real activity.

---

## 4. Verifying demo mode

```bash
# inside the venv / same process env
python -c "import os; print('DEMO_MODE=', os.environ.get('DEMO_MODE'))"

curl -s http://127.0.0.1:8000/healthz                 # {"status":"ok"}
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/dashboard   # 200 (not 401)
```
If `/dashboard` returns `401`, the flags did not reach the process — see `docs/00-start-here/TROUBLESHOOTING_GUIDE.md` §1–§3.

---

## 5. Toggling individual engines for a demo

All deterministic engines default OFF and are safe to enable for a walkthrough (set in `.env`, restart):
```bash
ROI_CENTER_ENABLED=true            # Executive ROI & Value Realization Center
SUFFICIENCY_ENGINE_ENABLED=true    # Evidence sufficiency scoring
EVIDENCE_TIMELINE_ENABLED=true     # Evidence timeline
# ... see docs/developer-manual/ENVIRONMENT_CONFIGURATION.md §5
```

---

## 6. Running ECS in Demo Mode (B — connector demo, Docker)

### Required
- Docker + Docker Compose.

### Exact commands
```bash
# Bring up platform + source systems + SonarQube, seed 6 apps, sync, verify — one shot:
./demo-data/recreate_demo.sh
```
Or step by step:
```bash
docker compose up -d                                   # ecs + postgres x2 + pgvector + redis + minio
docker compose --profile sources up -d                  # gitea + jenkins
docker compose --profile demo-connectors up -d          # sonarqube-demo + ubuntu-demo
./demo-data/seed_demo_environment.sh                    # seed 6 apps; writes demo-data/.gitea_token
export GITEA_TOKEN=$(cat demo-data/.gitea_token)
docker compose up -d ecs                                 # restart ECS with the token
for c in gitea jenkins sonarqube; do curl -s -X POST localhost:8000/api/platform/sync/$c; done
```

### Required files (mode B)
- `demo-data/.gitea_token` — generated by the seed script; wired into ECS via `GITEA_TOKEN`.
- `demo-data/sonar-demo/app.py` (scanned), `demo-data/jenkins/init.groovy.d/*` (Jenkins bootstrap), `demo-data/gitleaks-sample/` (gitleaks connector).

### Seeded applications
`mobile-banking`, `net-banking`, `upi`, `payments`, `treasury`, `api-gateway` — each created identically across Gitea (repo+commits+PR), Jenkins (job+build), and SonarQube (project+scan) so ECS correlates one Commit → Build → Scan chain per app.

### Expected behaviour (mode B)
```bash
curl -s http://localhost:8000/readyz                   # {"status":"ready", ...}
curl -s http://localhost:8000/api/platform/health      # total evidence + by_source + by_type
```
UI:
```
http://localhost:8000/mvp/integration-health?role=admin&user=Admin
http://localhost:8000/mvp/evidence-explorer?role=admin&user=Admin
```

### Known limitations (mode B)
- SonarQube takes 1–3 minutes to report `UP` before it accepts scans (the seed script waits).
- The SonarQube scanner runs as a `docker run` container on the compose network; it needs Docker socket access (`/var/run/docker.sock` is mounted into `ecs`).
- `recreate_demo.sh` runs `down -v` — it **destroys volumes** (a clean slate). Don't run it if you need to keep existing data.
- Source systems are behind profiles — a plain `docker compose up` will **not** start Gitea/Jenkins/SonarQube.

---

## 7. Leaving demo mode

Set `DEMO_MODE=false` and `ECS_AUTH_ENABLED=true` (defaults), configure an IdP (`ECS_AUTH_PROVIDER` + Azure/OIDC values), and progressively enable the RBAC flags. ECS is secure-by-default the moment `DEMO_MODE` is off and auth is enabled.
