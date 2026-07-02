# ECS Operator Guide (Knowledge Transfer)

**Audience:** operations owners, platform/IT-ops engineers running ECS day-to-day. **Goal:** run, monitor, collect evidence, and troubleshoot. Grounded in `app/routes_platform.py`, `ecs_platform/ingestion.py`, `scripts/`, `docs/operations/ecs_runbook.md`.

---

## 1. Start / stop

```bash
# Local (demo)
DEMO_MODE=true ECS_AUTH_ENABLED=false ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# Docker stack
docker compose up -d        # start    |    docker compose down     # stop
docker compose logs -f ecs  # tail app logs
```

## 2. Health & readiness

| Check | Endpoint | Healthy = |
|---|---|---|
| Liveness | `GET /healthz` | 200 |
| Readiness | `GET /readyz` | 200 |
| Platform/connectors | `GET /api/platform/health` | lists 12 connectors + DB status |
| Demo readiness | `python scripts/validate_demo_readiness.py` | `READY`, 0 defects |

## 3. Evidence collection operations

- **Scheduler** (`/mvp/scheduler`): run / retry / pause / resume collection jobs; watch success rate.
- **Integrations** (`/mvp/integrations`, `/mvp/integration-health`): connector status; **Sync Now**.
- **Bulk upload** (`/mvp/upload`): mass import with validation/dedup/auto-map.
- **Evidence Explorer** (`/mvp/evidence-explorer`): verify collected rows + correlations.

Connectors (12): Gitea, GitHub, SonarQube, Jenkins, Jira, Confluence, Figma, ServiceNow, Teams, SharePoint, Prisma Cloud, Azure DevOps (+ ops-layer Linux/PostgreSQL/Trivy/Gitleaks). Disabled by default; enable via env flag.

## 4. Monitoring what matters

| Signal | Where |
|---|---|
| Connector success rate | `/mvp/scheduler`, `/mvp/integration-health` |
| Evidence freshness/decay | `/mvp/evidence-health`, `/mvp/lifecycle` |
| Approval throughput / SLA | `/mvp/evidence-approval` |
| Governance data quality | `/mvp/governance-quality` |
| AI ops investigations | `/mvp/ai-ops-assistant` |

## 5. Routine operations

| Task | How |
|---|---|
| Seed/refresh demo data | `demo-data/recreate_demo.sh` (Docker) / `seed_demo_workflow_state()` (runtime) |
| Run validators | `scripts/validate_demo_readiness.py`, `validate_audit_prep.py`, `validate_framework_loader.py` |
| Run tests | `./venv/bin/pytest` (39 suites) |
| Reset DB | per `docs/RECOVERY_RUNBOOK.md` |

## 6. Troubleshooting (top symptoms)

| Symptom | Root cause | Resolution | Verify |
|---|---|---|---|
| 401/403 on every page | `ECS_AUTH_ENABLED=true` without IdP | Set demo flags or configure OIDC | Page loads |
| Pages show "Repository unavailable" | Postgres down | Start DB / use demo mode (auto-fallback) | `/api/platform/health` |
| Port 8000 in use | Stale uvicorn | `lsof -i:8000` then kill | Server starts |
| Connector "disabled" | `ECS_<X>_ENABLED` not set | Set flag + creds, `up -d ecs` | Integration Health = Connected |
| `.env` not taking effect | edited after start | restart app | values visible |

Full table: `docs/TROUBLESHOOTING_GUIDE.md` and `docs/operations/ecs_runbook.md`.

## 7. Demo operations

`DEMO_MODE=true ECS_AUTH_ENABLED=false` → all pages work with synthetic data, no external systems. Validate with the readiness script before any demo (expect READY).

## 8. Escalation

- Demo broken → run validator, check `/healthz`, review `docs/AUDIT/ECS_DEMO_READINESS_REPORT.md` checklist.
- Real-mode collection failing → Integration Health + `docker compose logs -f ecs`.
