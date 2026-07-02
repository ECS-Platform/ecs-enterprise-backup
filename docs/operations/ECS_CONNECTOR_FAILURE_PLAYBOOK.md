# ECS Connector Failure Playbook

**Purpose:** diagnose and recover evidence-collection connector failures. Grounded in `docker-compose.yml`, `config/integrations.yaml`, `ecs_platform/connectors/`, `ecs_platform/ingestion.py` (`health_overview`, `sync_connector`), `app/routes_platform.py`, `demo-data/SAAS_CONNECTOR_READINESS.md`. Documentation only.

> **Design baseline:** all 12 connectors are **interface-complete and disabled by default**. A connector goes live by setting `ECS_<X>_ENABLED=true` + credentials in host `.env` and restarting (`docker compose up -d ecs`) — **no rebuild, no code change**. `ConnectorFactory` resolves types from `_REGISTRY`.

---

## 1. Connector inventory

| Connector | Enable flag | Key env | Type |
|---|---|---|---|
| Gitea | (self-hosted, `sources`) | `GITEA_URL`, `GITEA_TOKEN` | SCM |
| GitHub | `ECS_GITHUB_ENABLED` | `GITHUB_URL`, `GITHUB_ORG`, `GITHUB_TOKEN` | SCM |
| SonarQube | (demo `sources`) | `SONAR_URL`, `SONAR_USER`, `SONAR_PASSWORD` | Code quality |
| Jenkins | (demo `sources`) | `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN` | CI |
| Jira | `ECS_JIRA_ENABLED` | `JIRA_URL/USER/TOKEN` | Issues |
| Confluence | `ECS_CONFLUENCE_ENABLED` | `CONFLUENCE_URL/USER/TOKEN` | Docs |
| Figma | `ECS_FIGMA_ENABLED` | `FIGMA_URL`, `FIGMA_TOKEN`, `FIGMA_TEAM_IDS` | Design |
| Teams | `ECS_TEAMS_ENABLED` | `MS_TENANT_ID/CLIENT_ID/CLIENT_SECRET`, `MS_GRAPH_URL` | Collaboration |
| SharePoint | `ECS_SHAREPOINT_ENABLED` | `MS_*`, `SHAREPOINT_SITE_ID` | Docs |
| ServiceNow / Prisma Cloud / Azure DevOps | per `integrations.yaml` | provider creds | ITSM / Cloud / DevOps |
| Ops-layer: Linux, PostgreSQL, Trivy, Gitleaks | container/query config | `ECS_LINUX_CONTAINER`, `ECS_GITLEAKS_SCAN_PATH`, etc. | Infra/security scans |

---

## 2. First diagnosis

```bash
curl -fsS localhost:8000/api/platform/health     # per-connector status from health_overview()
```
Or open **Integration Health** (`/mvp/integration-health`). Each connector reports a state; disabled connectors report `detail: "disabled"`.

| State | Meaning |
|---|---|
| `Connected/Authenticated` | Healthy |
| `disabled` | Flag not set (expected if not in use) |
| `auth failed` | Bad/expired credential |
| `unreachable` | Network/URL/DNS issue |
| `error` | See app logs |

---

## 3. Failure scenarios → recovery

| Symptom | Root cause | Recovery | Verify |
|---|---|---|---|
| Connector `disabled` but should be live | `ECS_<X>_ENABLED` unset | set flag + creds in host `.env`; `docker compose up -d ecs` | health = Connected |
| `auth failed` | expired/rotated token, wrong scope | rotate credential (least-privilege scopes per SAAS_CONNECTOR_READINESS); update `.env`; restart | re-sync ok |
| `unreachable` | URL wrong, DNS, firewall, source down | verify URL/network; for self-hosted check the container (`gitea`/`jenkins`/`sonarqube-demo`) is up | curl the source URL |
| Sync runs but 0 evidence | wrong org/project/site id, empty source | check `GITHUB_ORG`/`SHAREPOINT_SITE_ID`/team ids | Evidence Explorer rows |
| Teams/SharePoint fail despite creds | missing Graph env passthrough | confirm `MS_*` + `SHAREPOINT_SITE_ID` present (these were a known gap, now wired) | health = Connected |
| Partial/slow sync | rate limiting, large repo | back off, schedule off-peak, paginate | sync completes |
| Query-driven connector errors | DB/SSH/API execution gated | `DatabaseConnector/SSHConnector/APIConnector` raise `NotImplementedError` by design — use supported connectors | n/a (expected) |

---

## 4. Manual sync / re-trigger

```bash
# Single connector (admin; mutation-guarded)
curl -X POST "localhost:8000/api/platform/sync/<connector>?role=admin&user=ops"
# All connectors
curl -X POST "localhost:8000/mvp/platform/sync-all?role=admin&user=ops"
```
Then verify rows in Evidence Explorer (`/mvp/evidence-explorer`) and that control/framework mappings flow into Evidence Reuse + Framework Coverage.

---

## 5. Onboarding / re-enabling a connector (from readiness doc)

1. Create credential in source system (API token / PAT / Entra app + secret).
2. Grant minimum read scopes; admin-consent for Teams/SharePoint.
3. Add env vars to host `.env` (never hardcode in YAML).
4. `ECS_<X>_ENABLED=true`.
5. `docker compose up -d ecs` (re-reads env; no rebuild).
6. Integration Health → `Connected` → **Sync Now**.
7. Evidence Explorer → filter by source chip → confirm rows.

---

## 6. Impact & containment

- A failed connector affects **only its evidence stream** — ECS keeps serving all other data.
- Containment: disable the failing connector (`ECS_<X>_ENABLED=false`) to stop error noise; proceed degraded; fix offline.
- Demo mode is unaffected (synthetic data, no live connectors).

---

## 7. Escalation

L1 (this playbook: flags, restart, re-sync) → **L2 platform eng** (network, factory/registry, source containers) → **source-system owner** (credentials, scopes, source outages). Record connector, error state, and remediation in the incident log.
