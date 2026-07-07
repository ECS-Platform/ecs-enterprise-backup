# ECS API Reference

Reference for the **implemented** HTTP APIs of ECS. Every endpoint below is
enumerated from the live FastAPI app (`app.main:app`) — **no endpoints are
invented**. Routes are registered by the per-module route registrars
(`app/main.py` + `modules/*/routes/*`, `app/routes_*`).

> Regenerate the route list any time with:
> ```bash
> PYTHONPATH=. python -c "from app.main import app; import json; \
>   print('\n'.join(sorted(f\"{','.join(sorted(m for m in r.methods if m in ('GET','POST','PUT','DELETE','PATCH')))} {r.path}\" \
>   for r in app.routes if getattr(r,'methods',None) and getattr(r,'path',''))))"
> ```

**Conventions**
- Most endpoints accept `role` and `user` query params (demo persona context).
- In `DEMO_MODE=true` auth is bypassed; in production, auth/RBAC apply.
- Audit-intelligence responses follow the house shape: success `{"ok": true, …}`,
  error `{"ok": false, "status": "error", "message": …, "errors": […]}`.
- List endpoints under `/api/audit/*` paginate with `limit` / `offset` and return
  a `page` block (see [../DEVELOPER/PERFORMANCE_AND_HARDENING_GUIDE.md](../DEVELOPER/PERFORMANCE_AND_HARDENING_GUIDE.md)).
- No secrets are ever returned; connector config is masked (`SET`/`MISSING`).

---

## Health & readiness

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/healthz` | Liveness probe. |
| GET | `/readyz` | Readiness (repository connectivity). |
| GET | `/api/platform/health` | Platform/connector health. |
| GET | `/api/audit/health` | Audit-intelligence health incl. adapter registry summary. |

---

## Audit Intelligence API (`/api/audit/*`)

### Dashboards
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/audit/dashboard` | Composite executive-readiness payload. |
| GET | `/api/audit/dashboard/{section}` | A single dashboard section (allow-listed). |

### Assets & mapping
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/audit/assets` | Paginated asset inventory + coverage (`limit`,`offset`,`docker_compose`,`enterprise_grc`). |
| GET | `/api/audit/assets/technology-inventory` | Technology inventory across assets. |
| GET | `/api/audit/assets/fingerprints` | Fingerprint report for discovered assets. |
| GET | `/api/audit/mapping` | Paginated mapping rows + catalog stats. |
| GET | `/api/audit/mapping/search` | Mapping search (`query`,`technology`,`framework`,`limit`,`offset`). |
| GET | `/api/audit/mapping/technologies` | All technologies with coverage counts. |
| GET | `/api/audit/mapping/frameworks` | All frameworks with coverage counts. |
| GET | `/api/audit/mapping/graph` | Technology→control→framework graph. |
| GET | `/api/audit/mapping/stats` | Mapping coverage summary. |
| GET | `/api/audit/mapping/technology/{technology}` | Detail for one technology (404 if unknown). |
| GET | `/api/audit/mapping/framework/{framework}` | Detail for one framework (404 if unknown). |

### Evidence runs
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/audit/runs` | Paginated list of evidence runs. |
| POST | `/api/audit/runs` | Start a run (`scope_kind` required; `scope_value`,`control_ids`,`asset_id`). |
| GET | `/api/audit/runs/{run_id}` | Fetch one run (404 if unknown). |
| POST | `/api/audit/runs/{run_id}/retry` | Retry failed records (404 if unknown). |
| POST | `/api/audit/runs/{run_id}/cancel` | Cancel a run (404 if unknown). |
| GET | `/api/audit/runs/{run_id}/validation` | Validation results + compliance for a run. |

### Evidence repository
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/audit/evidence` | Paginated evidence search (`query`,`technology`,`framework`,`asset_id`,`verdict`,`tag`,`latest_only`). |
| GET | `/api/audit/repository` | Alias of `/api/audit/evidence`. |
| GET | `/api/audit/evidence/stats` | Repository statistics. |
| GET | `/api/audit/evidence/{evidence_key}/versions` | All versions for an evidence key. |
| GET | `/api/audit/evidence/{evidence_key}/timeline` | Timeline of events for an evidence key. |

### Observations
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/audit/observations` | Paginated observations (`status`,`severity`,`framework`,`technology`). |
| GET | `/api/audit/observations/summary` | Observation roll-up. |
| GET | `/api/audit/observations/{obs_id}` | Fetch one observation (404 if unknown). |
| POST | `/api/audit/observations/{obs_id}/transition` | Workflow transition (`to_status` required; 400 on invalid). |

### Evidence packs
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/audit/packs` | Base: available pack types + repository summary. |
| GET | `/api/audit/packs/{pack_type}/{scope}` | Build a pack (evidence/framework/asset/technology); paginated `items`. |
| POST | `/api/audit/packs/application` | Build an application pack (`application`,`asset_ids`). |

### Integrations
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/audit/integrations` | Masked config for all adapters (no secrets). |
| GET | `/api/audit/integrations/health` | Config-based health for all adapters. |
| GET | `/api/audit/integrations/{name}/health` | Health for one adapter (404 if unknown). |

---

## Platform API (`/api/platform/*`)

| Method | Path (selected) | Purpose |
|--------|-----------------|---------|
| GET | `/api/platform/inventory` | Application/asset inventory. |
| GET | `/api/platform/control-coverage` | Control coverage. |
| GET | `/api/platform/framework-coverage` | Framework coverage. |
| GET | `/api/platform/evidence` · `/evidence-reuse` · `/reuse-demonstrations` | Evidence + reuse views. |
| GET | `/api/platform/audit-readiness` · `/executive-summary` · `/scorecard` · `/crosswalk` | Readiness & executive views. |
| GET | `/api/platform/assistant` | Governance assistant. |
| GET | `/api/platform/rag/status` · `/rag/llm` · `/rag/gemini` | RAG status/query. |
| POST | `/api/platform/rag/reindex` · `/rag/warm` | RAG maintenance. |
| POST | `/api/platform/sync/{connector}` | Trigger a connector sync. |

## Demo API (`/api/demo/*`)
Read-only demo datasets powering the demo dashboards: `overview`, `status`,
`banking-applications`, `frameworks`, `cio-executive`, `risk-heatmap`,
`audit-history`, `vapt`, `ai-governance`, `prompt-audit`, `hallucinations`,
`token-usage`, `drift`, `evidence-lineage`, `servicenow`, `kpi-drill`.

## Framework, onboarding, drilldown, workflow & filter APIs
Additional implemented groups (see the regenerate command above for the full list):
`/api/framework/*`, `/api/framework-loader/*`, `/api/framework-onboarding/*`,
`/api/ecs/filters/*`, `/api/ecs/universal-drill`, `/api/ecs/workflow-drill`,
`/api/module-kpi/drill`, `/api/grc-demo/*`, `/api/onboarding/*`,
`/api/exceptions/raise`, `/api/evidence-workflow/summary`.

---

## Notes on the Predefined Query / Aerospike flow

Predefined-query execution (including **Aerospike** `ASX-*` controls) is driven by
the server-rendered Predefined Queries screen (`/mvp/predefined-queries`) and the
`predefined_queries_engine.run_predefined_query(control_id, user)` entry point
rather than a dedicated public REST endpoint. See
[../DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md](../DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md)
and [../DEVELOPER/AEROSPIKE_LOCAL_TESTING_GUIDE.md](../DEVELOPER/AEROSPIKE_LOCAL_TESTING_GUIDE.md).
