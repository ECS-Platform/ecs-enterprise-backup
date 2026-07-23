# ECS Developer Onboarding Manual — Asset-Driven Scheduler

A focused onboarding companion for developers working on (or extending) the
**UAT asset-driven scheduler & evidence routing** layer.

> General ECS onboarding (environment setup, repo structure, predefined-query
> module, running the app) is already covered in
> [README_DEVELOPER.md](README_DEVELOPER.md). **Start there** for first-time setup.
> This manual assumes you have a working local environment and zooms in on the
> asset-scheduler subsystem and how it reuses the rest of ECS.

---

## 1. What the scheduler does (in one minute)

It reads an **asset inventory** (YAML), figures out **what technology** each asset
is, and decides **how to collect its evidence** — via an existing enterprise
connector or the baseline predefined-query collector — then prints a **plan**. In
`--dry-run` (the default) it makes **no** network/connector/query calls.

Full design: [UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](../scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md).

---

## 2. The 60-second demo

```bash
# From the repo root, offline + safe (localhost/mock inventory):
PYTHONPATH=. python scripts/run_uat_asset_scheduler.py \
    --config config/uat_assets.local.yaml --dry-run

# JSON (for pipelines / inspection):
PYTHONPATH=. python scripts/run_uat_asset_scheduler.py \
    --config config/uat_assets.local.yaml --json
```

You should see baseline collectors (PostgreSQL, NGINX, Redis, Linux), enterprise
connector routes (SonarQube, SharePoint, Jira, ServiceNow), one unsupported
fallback asset, and a plan summary. No credentials are printed.

---

## 3. Where the code lives

| Piece | Path |
|-------|------|
| Scheduler service (loader, classifier, router, planner, dry-run) | `modules/audit_intelligence/services/asset_scheduler.py` |
| CLI | `scripts/run_uat_asset_scheduler.py` |
| Local/mock inventory (safe for CI/demo) | `config/uat_assets.local.yaml` |
| UAT template (placeholders only) | `config/uat_assets.template.yaml` |
| Tests (offline) | `tests/test_uat_asset_scheduler.py` |

It **reuses** (does not duplicate):
- `engines/technology_fingerprint.py` — technology classification.
- `engines/asset_discovery.py` — asset normalization (`discover_from_manual`).
- `engines/technology_control_mapping.py` — technology → controls/frameworks.
- `engines/evidence_orchestrator.py` — `resolve_scope`.
- `modules/operations/integrations/` — the 11 connectors (registry only; never
  modified here).
- `services/evidence_service.py` — optional baseline execution.

---

## 4. Mental model: how one asset flows

```
raw asset dict (from YAML)
  → asset_discovery.discover_from_manual()   # normalize + fingerprint
    → Asset(technology=..., confidence=...)
      → asset_scheduler.classify_asset()      # decide the route
        → AssetClassification(route=baseline|connector|unsupported)
          → asset_scheduler.plan_evidence()   # bounded, deterministic plan
            → EvidencePlan(jobs=[...], unsupported=[...])
```

Route precedence: **connector** (by `asset_type`/tech) → **baseline** (tech has
predefined controls) → **unsupported** (manual review).

---

## 5. Common tasks

### Add a new asset to the local demo
Edit `config/uat_assets.local.yaml` and add an entry under `assets:` using
**localhost/mock** values only (no real hosts/IPs/secrets). Re-run the CLI.

### Route a new connector
The connector already exists in `modules/operations/integrations/`. Add one line
to `_CONNECTOR_ROUTES` in `asset_scheduler.py`:
```python
_CONNECTOR_ROUTES = {
    ...,
    "my_asset_type": "my_adapter_module",
}
```
Add a routing test mirroring `test_jira_routing`.

### Add a new baseline technology
Nothing to do in the scheduler — it flows automatically from the predefined-query
catalog + fingerprint engine. Just make sure the fingerprint engine recognizes it
(see `_TEXT_RULES` / `_PORT_RULES` in `technology_fingerprint.py`).

### Point at real UAT
```bash
cp config/uat_assets.template.yaml config/uat_assets.uat.yaml   # keep OUT of Git
# edit with real UAT hostnames via env vars; never inline secrets/IPs
PYTHONPATH=. python scripts/run_uat_asset_scheduler.py --config config/uat_assets.uat.yaml --dry-run
```

---

## 6. Running the tests

```bash
PYTHONPATH=. pytest tests/test_uat_asset_scheduler.py -q
```

These are fully offline (no app startup, no network) and run in well under a
second. Add a test for any routing/classification change you make.

---

## 7. Safety rules (do not break)

- **Never** open a socket in `dry_run()`; connector readiness is config-only
  (`is_configured()` / `masked_config()`), never `health_check()`.
- **Never** commit real IPs, hostnames, tenant IDs, or secrets. The local config
  is localhost/mock; the template is placeholders only.
- **Never** re-implement or modify connector code — route to the existing adapter.
- Keep the plan **bounded** (`_MAX_ASSETS`, `_MAX_CONTROLS_PER_ASSET`) and
  **deterministic** (stable sort).

---

## 8. Related docs

- [UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md](../scheduler/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md) — full design.
- [ASSET_DISCOVERY_GUIDE.md](../scheduler/ASSET_DISCOVERY_GUIDE.md) — asset discovery & fingerprinting.
- [TECHNOLOGY_MAPPING_GUIDE.md](TECHNOLOGY_MAPPING_GUIDE.md) — technology → control → framework.
- [INTEGRATION_ADAPTERS_GUIDE.md](../connectors/INTEGRATION_ADAPTERS_GUIDE.md) — the 11 connectors.
- [../operations/UAT_VALIDATION_RUNBOOK.md](../operations/UAT_VALIDATION_RUNBOOK.md) — operator UAT runbook.
- [README_DEVELOPER.md](README_DEVELOPER.md) — general developer onboarding.
