# ECS Deployment Architecture

> **Current** sections are sourced strictly from `Dockerfile`, `docker-compose.yml`, `config/`,
> and `app/routes_platform.py`. **Future / HA / DR** sections are explicitly
> **[RECOMMENDATION]** — they are target-state designs, not present in the repo today.

---

## 1. Current Deployment Model

ECS ships as a single container image built from `python:3.12-slim` (`Dockerfile`) running
`uvicorn app.main:app --host 0.0.0.0 --port 8000`. `docker-compose.yml` orchestrates the app plus
backing services for local/demo use.

**Image build (`Dockerfile`):** installs `docker.io` + pip `requirements.txt`; copies `app/`,
`modules/`, `demo-data/`, `ecs_platform/`, `config/`; exposes `8000`.

**Compose services (`docker-compose.yml`):**

| Service | Image | Host port | Role | Profile |
|---|---|---|---|---|
| `ecs` | `build: .` | 8000 | FastAPI app (dev `--reload`, source bind-mounts) | default |
| `postgres-demo` | `postgres:16` | 5432 | Demo DB `ecs_demo` | default |
| `postgres` | `postgres:16` | 5433 | Evidence repository `ecs_repository` (healthcheck, volume) | default |
| `pgvector` | `pgvector/pgvector:pg16` | 5434 | Vector store `ecs_vectors` (healthcheck, volume) | default |
| `redis` | `redis:7-alpine` | 6379 | Cache/queue (persisted) | default |
| `minio` | `minio/minio:latest` | 9002 (API), 9001 (console) | Object store (healthcheck, volume) | default |
| `ubuntu-demo` | `ubuntu:22.04` | — | Linux connector target | `demo-connectors` |
| `sonarqube-demo` | `sonarqube:lts-community` | 9000 | SonarQube connector target | `demo-connectors` |
| `gitea` | `gitea/gitea:1.22` | 3000, 2222 | Git source system | `sources` |
| `jenkins` | `jenkins/jenkins:lts` | 8080, 50000 | CI source system | `sources` |

`ecs` `depends_on`: `postgres-demo`, `postgres`, `pgvector`; mounts the host Docker socket
(`/var/run/docker.sock`) and `extra_hosts: host.docker.internal:host-gateway` to reach a host-local
Ollama LLM. Named volumes: `ecs_repo_data`, `ecs_vector_data`, `ecs_redis_data`, `ecs_minio_data`,
`ecs_gitea_data`, `ecs_jenkins_data`.

```mermaid
graph TD
  subgraph Host["Docker host (compose)"]
    ECS["ecs :8000 (uvicorn)"]
    PGD[("postgres-demo :5432 ecs_demo")]
    PGR[("postgres :5433 ecs_repository")]
    PGV[("pgvector :5434 ecs_vectors")]
    RDS[("redis :6379")]
    OBJ[("minio :9002/:9001")]
    subgraph demoConnectors["profile: demo-connectors"]
      UB["ubuntu-demo"]
      SQ["sonarqube-demo :9000"]
    end
    subgraph sources["profile: sources"]
      GIT["gitea :3000"]
      JEN["jenkins :8080"]
    end
  end
  OLL["host Ollama :11434 (host.docker.internal)"]
  ECS --> PGD & PGR & PGV & RDS & OBJ
  ECS -. connectors .-> UB & SQ & GIT & JEN
  ECS -. LLM .-> OLL
```

**Config plane:** `config/` (`auth.yaml`, `rbac.yaml`) mounted read-only at `/app/config`
(`ECS_CONFIG_DIR=/app/config`). Connector/LLM credentials are injected via host environment (compose
uses `${VAR:-default}` and never hardcodes SaaS secrets).

---

## 2. Container Architecture

```mermaid
graph TD
  subgraph Image["ECS container (python:3.12-slim)"]
    UV["uvicorn worker"]
    APP["app.main:app"]
    MODS["modules/* (engines, templates, static)"]
    PLAT["ecs_platform/*"]
    CFG["/app/config (ro)"]
    DEMO["/app/demo-data"]
  end
  UV --> APP --> MODS
  APP --> PLAT
  APP --> CFG
  MODS --> DEMO
```

- **Single process / single worker** by default (`CMD` has no `--workers`); compose dev adds
  `--reload`. **[NOTE]** because business state is in-process (`ecs_state`), multi-worker scaling is
  not safe until state is externalized (see Enterprise Architecture Review, R1).
- Docker socket mount enables container-aware connectors (e.g. Linux connector targeting
  `ubuntu-demo`).

---

## 3. Runtime Architecture

```mermaid
graph LR
  Client["Browser"] --> MW["_no_cache_html + AuthenticationMiddleware"]
  MW --> Routes["Domain route registrars"]
  Routes --> Engines["modules/* engines/services"]
  Engines --> State["ecs_state (in-process)"]
  Engines -->|optional| Repo["ecs_platform repository (PostgreSQL)"]
  Engines -->|optional| Vec["pgvector vector store"]
  Engines -->|optional| RAG["LLM-RAG (Ollama/Gemini)"]
  Engines -->|optional| ObjS["MinIO object store"]
```

- **Startup lifespan** (`app/main.py`): seeds demo workflow state, refreshes repository from
  frameworks, self-heals governance, validates predefined queries, best-effort initializes DB schema,
  warms LLM models in background.
- **Health/readiness:** `GET /healthz` (liveness), `GET /readyz` (readiness incl. PostgreSQL),
  `GET /api/platform/health` (connector health) — `app/routes_platform.py`.

---

## 4. Network Architecture (current)

```mermaid
graph TD
  User --> P8000["ecs :8000 (HTTP)"]
  Admin --> P9001["minio console :9001"]
  Ops --> P5432["postgres-demo :5432"]
  Ops --> P5433["postgres :5433"]
  Ops --> P5434["pgvector :5434"]
  Ops --> P6379["redis :6379"]
  Ops --> P9000["sonarqube :9000 (profile)"]
  Ops --> P3000["gitea :3000 (profile)"]
  Ops --> P8080["jenkins :8080 (profile)"]
```

- All services share the default compose bridge network; ECS reaches them by service DNS name
  (`postgres-demo`, `pgvector`, `minio`, `redis`, `sonarqube-demo`, `gitea`, `jenkins`).
- **No TLS termination in the container** — HTTP on 8000. TLS is expected at an ingress/LB in
  non-local deployments **[ASSUMPTION]**.
- LLM reached out-of-network via `host.docker.internal:11434`.

---

## 5. Future Cloud Deployment Architecture **[RECOMMENDATION]**

Target state externalizes state and runs the stateless web tier behind managed services.

```mermaid
graph TD
  Users --> WAF["WAF / CDN"]
  WAF --> LB["Managed Load Balancer (TLS)"]
  LB --> ING["Ingress / API Gateway"]
  subgraph K8s["Kubernetes / container platform"]
    ECS1["ecs replica 1"]
    ECS2["ecs replica 2"]
    ECSn["ecs replica N"]
    RAGSVC["LLM-RAG service (separate pool)"]
  end
  ING --> ECS1 & ECS2 & ECSn
  ECS1 & ECS2 & ECSn --> PG[("Managed PostgreSQL (repository + governance)")]
  ECS1 & ECS2 & ECSn --> PGV[("Managed pgvector")]
  ECS1 & ECS2 & ECSn --> CACHE[("Managed Redis (sessions/state/cache)")]
  ECS1 & ECS2 & ECSn --> OBJ[("Object storage (evidence files)")]
  ECS1 & ECS2 & ECSn --> SM["Secret manager"]
  RAGSVC --> LLM["Managed/Hosted LLM"]
```

Prerequisites (from current gaps): externalize `ecs_state` to PostgreSQL/Redis, enforce RBAC,
integrate a secret manager, pin dependencies, run multiple stateless replicas with `--workers`.

---

## 6. High Availability (HA) Architecture **[RECOMMENDATION]**

```mermaid
graph TD
  LB["LB (multi-AZ, health-checked via /healthz,/readyz)"]
  LB --> AZ1["AZ-1: ecs replicas"]
  LB --> AZ2["AZ-2: ecs replicas"]
  AZ1 & AZ2 --> PGHA[("PostgreSQL primary + standby (sync replication)")]
  AZ1 & AZ2 --> REDISHA[("Redis (replicated/clustered)")]
  AZ1 & AZ2 --> OBJHA[("Object storage (multi-AZ)")]
```

- **Stateless replicas** across ≥2 AZs; LB uses existing `/healthz` and `/readyz` probes.
- **PostgreSQL** primary/standby with automatic failover; **Redis** replication; **object storage**
  multi-AZ redundancy.
- No single point of failure in the web tier once state is externalized.

---

## 7. Disaster Recovery (DR) Architecture **[RECOMMENDATION]**

```mermaid
graph LR
  subgraph Primary["Primary region"]
    P["ECS + PostgreSQL + Object store"]
  end
  subgraph DR["DR region"]
    D["ECS (warm) + PostgreSQL standby + Object replica"]
  end
  P -- "async replication / WAL shipping" --> D
  P -- "object replication" --> D
  Backup["Periodic backups -> immutable storage"]
  P --> Backup
```

- **Replication:** async PostgreSQL replication / WAL shipping + object-store cross-region replication.
- **Backups:** scheduled PostgreSQL dumps + evidence object snapshots to immutable storage (supports
  banking retention requirements).
- **Targets:** define RPO/RTO **[RECOMMENDATION]**; suggested starting point RPO ≤ 15 min, RTO ≤ 1 hr.
- **Runbook:** see `docs/03-development/operations/ecs_runbook.md` for backup/recovery procedures.
