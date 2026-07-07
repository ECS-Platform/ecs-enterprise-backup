# ECS Documentation Audit Report

A targeted documentation-consistency audit performed alongside the Aerospike
support work and the API-reference addition. Scope is deliberately narrow (the
areas the change touches); it is **not** a full-repository doc rewrite.

**Date basis:** generated during the Aerospike integration change on branch
`cursor/predefined-queries-module`.

---

## 1. Aerospike references — consistent ✓

Aerospike is documented in exactly the right places, with no contradictions:

| Doc | Aerospike content |
|-----|-------------------|
| [DEVELOPER/AEROSPIKE_LOCAL_TESTING_GUIDE.md](DEVELOPER/AEROSPIKE_LOCAL_TESTING_GUIDE.md) | Primary guide: Docker, 20 `ASX-*` queries, run-query, dropdown troubleshooting, fingerprinting, scheduler, tests, limitations. |
| [DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md](DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md) | Scope updated to include Aerospike + cross-link to the guide. |
| [API/ECS_API_REFERENCE.md](API/ECS_API_REFERENCE.md) | Notes the predefined-query/Aerospike execution entry point. |

All three agree on: image `aerospike/aerospike-server:latest`, container
`ecs-aerospike`, host port **13000** (container 3000), namespace `test`, 20
controls `ASX-001…ASX-020`.

## 2. Connector count — consistent at 11 ✓

The enterprise integration adapter count is **11** everywhere it is stated
(ServiceNow, Archer, SharePoint/Teams/Outlook Graph, Jira, Confluence, SonarQube,
Checkmarx, Prisma Cloud, Tripwire). Verified in `README_DEVELOPER.md`,
`INTEGRATION_ADAPTERS_GUIDE.md`, `DEMO_RUNBOOK.md`, `E2E_SMOKE_TEST_GUIDE.md`,
`LEADERSHIP_DEMO_SCRIPT.md`, `PRODUCTION_READINESS_GAP_REGISTER.md`,
`ECS_DEVELOPER_ONBOARDING_GUIDE.md`, and `UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md`.

> Note: Aerospike is a **predefined-query technology (baseline collector)**, not an
> enterprise connector, so it does **not** change the "11 adapters" count. The
> historical `CHANGELOG.md` entry that says "9 adapters" is intentionally left as a
> point-in-time record (a later entry states "registry now 11").

## 3. Technology dropdown guidance — consistent ✓

The dropdown is documented as **data-driven** (built from distinct technologies of
loaded controls via `get_technology_filter_options()`), with a troubleshooting
checklist in the Aerospike guide (§5). This matches the code and the RCA:

> **Root cause of "a technology is missing from the dropdown":** the dropdown only
> lists technologies that have ≥1 loaded control. Aerospike was absent solely
> because no Aerospike controls existed; adding the `ASX-*` controls makes it
> appear for all peers after an app restart (no UI/seed/static-JS/DB change).

## 4. Docker port conflicts — consistent ✓

- **Gitea keeps host port 3000** (`docker-compose.yml` maps `"3000:3000"` for Gitea).
- **Aerospike uses host port 13000** (`${AEROSPIKE_HOST_PORT:-13000}:3000`), never
  host 3000. This is stated in the compose comments, `.env.example`, and the
  Aerospike guide, and enforced by `tests/test_aerospike_support.py`.

## 5. run-query examples — consistent ✓

Examples use the real entry point
`predefined_queries_engine.run_predefined_query(control_id, user)` and the real
screen `/mvp/predefined-queries`. No invented endpoints. Demo-mode behaviour
(deterministic `[DEMO]` output) is documented and matches the implementation.

## 6. Scheduler examples — consistent ✓

Examples use the real CLI
`python scripts/run_uat_asset_scheduler.py --config config/uat_assets.local.yaml --dry-run`
and describe Aerospike classifying as a **baseline_collector** — matching
`asset_scheduler.classify_asset` and the tests.

## 7. Broken links — none in changed/new docs ✓

All internal Markdown links in the new/updated docs were validated to resolve:
`AEROSPIKE_LOCAL_TESTING_GUIDE.md` and `API/ECS_API_REFERENCE.md` → **all links OK**.

## 8. Duplicate docs — none introduced ✓

- The Aerospike guide is the **single** source for Aerospike local testing; other
  docs cross-reference it rather than repeating content.
- `API/ECS_API_REFERENCE.md` is **new** (no prior API reference existed) and is
  generated from real routes, not duplicating the LLD's UI-to-API flow narrative.

## 9. Secrets / real IPs / bank values — none ✓

The Aerospike artifacts (compose service, `.env.example` block, connector,
catalog, guide) contain no secrets, no non-loopback IPs, and no bank-specific
values (enforced by a test). Secret placeholders (`AEROSPIKE_USER/PASSWORD`) are
blank.

---

## Residual recommendations (non-blocking, out of this change's scope)

- The docs index (`docs/README.md`) mixes lowercase/uppercase path casing in a few
  older links (e.g. `operations/` vs `OPERATIONS/`); a future normalization pass
  could tidy these. Pre-existing.
- A future enhancement could auto-generate the full endpoint list in
  `API/ECS_API_REFERENCE.md` from the OpenAPI schema in CI to prevent drift.
- When `cursor/final-closure-review-pack` merges, add its UAT execution checklist
  to the Aerospike guide's cross-references.
