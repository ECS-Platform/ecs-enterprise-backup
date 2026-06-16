# ECS — Local Development Guide

Day-to-day workflow for engineers actively changing ECS. Everything here is derived from the actual code (`app/main.py`, `app/env_bootstrap.py`, the route registrars, `modules/`, `scripts/`, `tests/`, `docker-compose.yml`).

---

## 1. Application startup flow (what happens on boot)

Entry point: `app/main.py`, ASGI app object `app` (`uvicorn app.main:app`).

1. **`.env` is loaded first.** The very first import in `app/main.py` is `from app import env_bootstrap`. `app/env_bootstrap.py::load_env()` loads the repo-root `.env` into `os.environ` (using `python-dotenv`, falling back to a built-in parser) with `override=False` so real env / container values still win. This guarantees `DEMO_MODE` and `ECS_AUTH_ENABLED` exist before auth/RBAC initialise.
2. **FastAPI app constructed** with `lifespan=ecs_lifespan`.
3. **Middleware installed:**
   - `_no_cache_html` — sends `Cache-Control: no-cache` on HTML responses (so template/inline-CSS edits show up without a hard refresh).
   - `register_authentication(app)` (`app/auth/`) — central auth middleware; **pass-through when auth is disabled**.
4. **Static mount:** `/static/ecs` → `modules/shared/static`.
5. **Templates:** a Jinja2 `ChoiceLoader` spanning eight template directories (the six module template dirs + `modules/shared/templates` + `app/templates`).
6. **Routes registered** (bottom of `app/main.py`): `register_mvp_routes`, `register_evidence_routes`, `register_platform_routes`, `register_governance_routes`, `register_ai_sdlc_routes`, `register_grc_demo_routes`.
7. **Lifespan (`ecs_lifespan`) runs on startup:**
   - `configure_logging()` + startup banner (`DEMO_MODE`, `ECS_AUTH_ENABLED`, `.env loaded`).
   - `refresh_repository_from_frameworks(source="startup")`.
   - `seed_demo_workflow_state()` — seeds deterministic demo workflow state.
   - `self_heal_governance()`.
   - `validate_startup()` — predefined-queries validation; logs results.
   - **Best-effort** `init_repository()` + `init_governance_schema()` (PostgreSQL) — never blocks startup; logs "unavailable" when no DB.
   - Flag-gated durable observation hydration (`OBSERVATIONS_DURABLE_ENABLED`).
   - LLM-RAG status check + background `warm_models()` thread (logs "disabled" when no provider).
   - `mark_startup_complete()` + `log_platform_ready(host="127.0.0.1", port=8000)`.

**Key consequence:** ECS boots fully with **no database and no LLM**. Those are optional, best-effort dependencies.

---

## 2. Backend startup process

```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

- `--reload` watches Python files and restarts on change.
- Default bind is `127.0.0.1:8000`. Add `--host 0.0.0.0 --port 8000` to expose it.
- Under Docker Compose, the `ecs` service runs uvicorn with `--reload` and `--reload-dir /app/app --reload-dir /app/modules --reload-dir /app/ecs_platform`, bind-mounting those directories so `.py` edits hot-reload without an image rebuild.

---

## 3. Frontend startup process

**There is no separate frontend build or dev server.** The UI is server-rendered Jinja2:

- Page templates and partials live under each module's `templates/` directory and `modules/shared/templates/`.
- Static assets (CSS/JS) are served from `modules/shared/static` at `/static/ecs` (e.g. `modules/shared/static/js/drilldown_engine.js`).
- Cache-busting: `app/main.py::asset_ver()` appends `?v=<mtime>` to static asset URLs; the `_no_cache_html` middleware prevents stale HTML.
- `package-lock.json` declares **no** packages — do **not** run `npm install`; there is nothing to build.

To see template/CSS/JS changes: just refresh the browser (with `uvicorn --reload` running, Python changes restart automatically; template/static changes are picked up on the next request).

---

## 4. Where code lives (module map)

| Concern | Location |
|---|---|
| App entry, route registrars, workflow endpoints | `app/main.py` |
| Env loading | `app/env_bootstrap.py` |
| Auth (middleware, providers, enforcement, scope) | `app/auth/` |
| MVP / platform / governance / AI-SDLC / GRC routes | `app/routes_mvp.py`, `app/routes_platform.py`, `app/routes_governance.py`, `app/routes_ai_sdlc_governance.py`, `app/routes_grc_demo.py`, `app/evidence_routes.py` |
| Executive dashboards, reports, ROI, demo metrics | `modules/executive_overview/` |
| Framework catalog, dashboards, control validation, ITPP | `modules/frameworks/` |
| Scheduler, bulk upload, integrations, connectors, AI-ops | `modules/operations/` |
| Evidence health/approval/lifecycle/completeness/audit-prep | `modules/governance/` |
| Risk register, CMDB, exceptions, heatmaps, correlation | `modules/enterprise_grc/` |
| SDLC gates, control tower, AI governance posture | `modules/ai_sdlc/` |
| Shared state, RBAC, drilldown, persona UI, workflow engine | `modules/shared/` |
| Connectors, evidence repository, vector store, RAG, config loader | `ecs_platform/` |
| YAML config | `config/` |

> **Shims:** several files under `app/` (e.g. `app/ecs_state.py`) re-export canonical implementations from `modules/*`. Prefer editing the canonical `modules/*` source.

---

## 5. Running tests

`pytest` is not in `requirements.txt`; install it once:

```bash
pip install pytest
```

There is **no `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `conftest.py`** — pytest uses discovery defaults over the `tests/` directory (39 suites, all `test_*.py`).

```bash
pytest                                  # full suite
pytest -q                               # quiet
pytest tests/test_roi_engine.py         # one file
pytest tests/test_roi_engine.py -v      # verbose
pytest -k "rbac"                         # by keyword (RBAC enforcement suites)
pytest tests/test_platform_certification.py
```

Representative suites (names indicate scope): `test_rbac_enforcement_phase2_step2b/c/d.py`, `test_rbac_scope_filtering_phase2_step3.py`, `test_authz_phase2.py`, `test_audit_durability_phase4.py`, `test_observation_durability_phase4_step3.py`, `test_sufficiency_engine_phase5_2a.py`, `test_evidence_intel_phase5_4.py`, `test_evidence_analytics_phase5_5.py`, `test_connectivity_assessment_phase5_3.py`, `test_roi_engine.py`, `test_ai_sdlc_*`, `test_platform_certification.py`, `test_universal_drilldown_engine.py`.

---

## 6. Validation & certification scripts

Beyond pytest, `scripts/` holds runnable validators/certifiers (each is a normal Python script; run with the venv active):

```bash
python scripts/validate_templates.py          # Jinja template audit (parse + macro + live render)
python scripts/validate_demo_engine.py         # demo overview + /api/demo/* endpoints
python scripts/validate_demo_readiness.py
python scripts/validate_audit_prep.py          # /mvp/audit-prep across roles
python scripts/validate_framework_loader.py    # framework loader end-to-end smoke
python scripts/validate_post_migration.py
python scripts/run_ecs_validation.py
python scripts/platform_certification.py
python scripts/module_focus_certification.py
python scripts/role_route_matrix_certification.py
```

Run `scripts/validate_templates.py` after any template change — it parses, audits macro contracts, and live-renders routes via a FastAPI TestClient.

---

## 7. Demo data lifecycle (Docker stack)

| Action | Command |
|---|---|
| Recreate everything (down -v → up → seed → sync → verify) | `./demo-data/recreate_demo.sh` |
| Seed 6 apps across Gitea/Jenkins/SonarQube | `./demo-data/seed_demo_environment.sh` |
| Seed governance data | `python demo-data/seed_governance.py` |
| Seed Jenkins / SonarQube / pipeline only | `./demo-data/seed_jenkins_demo.sh`, `./demo-data/seed_sonarqube_demo.sh`, `./demo-data/seed_pipeline_demo.sh` |
| Trigger ECS evidence collection (per connector) | `curl -X POST localhost:8000/api/platform/sync/<gitea\|jenkins\|sonarqube>` |

The in-memory **showcase** demo state (dashboards, 15-framework catalog) needs no seeding — it is generated deterministically on startup. The seed scripts populate the **connector-driven** evidence flow that requires the Docker stack.

---

## 8. Backup & restore (PostgreSQL repository)

Scripts under `scripts/backup` and `scripts/restore` (used only with the Docker/Postgres stack):

```bash
scripts/backup/backup.sh                       # dump the evidence repository to $BACKUP_DIR (default ./backups)
scripts/backup/validate_backup_restore.sh      # round-trip validation
scripts/restore/restore.sh <dump-file>         # restore from a dump
```

`BACKUP_DIR` (default `./backups`) and `BACKUP_RETENTION_DAYS` (default 14) are configured in `.env`. Backups contain sensitive evidence/audit data and are git-ignored (`backups/`, `*.dump`).

---

## 9. Logging

`modules/shared/services/ecs_logging.py` configures logging and emits the startup banner and platform-ready line. Components log with a category tag, e.g. `[ECSStartup]`, `[ECSPlatform]`, `[PredefinedQueries]`. The startup banner explicitly prints `DEMO_MODE`, `ECS_AUTH_ENABLED`, and how `.env` was loaded — read it first when behavior looks off.

---

## 10. Typical inner loop

```bash
source venv/bin/activate
uvicorn app.main:app --reload          # leave running in one terminal
# edit modules/<domain>/engines/*.py or templates/*.html
# refresh browser; reload restarts on .py changes
python scripts/validate_templates.py   # after template edits
pytest -k "<area>"                       # run the relevant suites
```
