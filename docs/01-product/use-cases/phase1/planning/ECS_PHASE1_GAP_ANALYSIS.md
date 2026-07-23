# ECS Phase 1 — Gap Analysis

**Type:** Documentation only. No code modified.
**Date:** 2026-06-17
**Companion:** `ECS_PHASE1_IMPLEMENTATION_BACKLOG.md` (item IDs B01–B24).

This document analyses the gap between **what ECS is today** and **what Phase 1
UAT/PROD requires**, organised by readiness dimension. The headline conclusion
from the repository and readiness-report review: ECS is **engineering-complete**;
the residual gap is **configuration, data, and operational provisioning**.

---

## 1. Current state (verified)

| Capability | State | Evidence |
|------------|-------|----------|
| Environment selection (`ECS_ENV`) | ✅ Implemented | `config/environment_loader.py`; 5 env files PASS validation |
| YAML-driven config (apps/dbs/connectors/targets/storage/auth/llm/reporting) | ✅ Implemented | `config/environments/_base.yaml` + per-env overrides |
| Hardcoded IP/URL elimination | ✅ Verified | repo scan: 0 public IPs in `modules/`,`ecs_platform/`,`app/` |
| Startup config validation | ✅ Implemented | `config/config_validation.py` + `app/main.py` strict-env gate |
| Connector model (12 connectors, URL + secret-env) | ✅ Implemented | `config/integrations.yaml` + `connectors.*` |
| Evidence repository abstraction (Postgres + demo fallback) | ✅ Implemented | `ecs_platform/repository`, `demo_governance.py` |
| AI provider abstraction (local Ollama default) | ✅ Implemented | `ecs_platform/llm_engine/provider.py`, `config/llm.yaml` |
| Demo experience (all personas/pages/drilldowns) | ✅ 100% | `nav_audit/final_demo_readiness_report.md` |

## 2. Target state (Phase 1 UAT/PROD)

Real endpoints + secrets + persistent stores + enterprise auth + observability,
with ECS deployable per environment by editing YAML only.

## 3. Gap matrix (current → target)

| # | Gap | Dimension | Category | Severity | Backlog |
|---|-----|-----------|----------|----------|---------|
| G1 | UAT/PROD endpoints are placeholders | Environment | Configuration | High | B01,B02,B04 |
| G2 | Live predefined-query connectors default to demo | Environment | Configuration | High | B03 |
| G3 | 10/15 application host slots empty | Environment | Configuration | Medium | B05 |
| G4 | Secrets not provisioned (UAT env vars / PROD vault) | Operational | Operations/Deployment | High | B06,B07 |
| G5 | No persistent evidence-repo Postgres in UAT/PROD | Operational | Deployment | High | B08 |
| G6 | Object store not provisioned (endpoint/TLS/creds) | Operational | Deployment | High | B09 |
| G7 | SSO/IdP not provisioned for PROD | Production | Deployment | High | B10 |
| G8 | DB drivers (`psycopg2`) absent from runtime | Operational | Deployment | Medium | B11 |
| G9 | Validation not enforced in CI/CD | Operational | Deployment | Medium | B12 |
| G10 | No automated per-env smoke gate | UAT | Testing | Medium | B13 |
| G11 | 2 pre-existing unit-test failures | UAT | Testing/Code | Medium | B14 |
| G12 | No load/concurrency baseline | UAT/Production | Testing | Medium | B15 |
| G13 | LLM/pgvector not provisioned in UAT/PROD | AI | Deployment/Ops | Medium | B16 |
| G14 | No monitoring/alerting | Operational | Operations | High | B17 |
| G15 | No backup/DR | Operational | Operations | High | B18 |
| G16 | TLS/cert lifecycle not managed | Production | Deployment | Medium | B19 |
| G17 | No prod config change-management sign-off | Production | Operations | Medium | B20 |
| G18 | Deployment runbook/secrets matrix incomplete | All | Documentation | Low | B21 |
| G19 | Oracle/MySQL/SQL Server live connectors missing | Architecture | Code Change | Medium | B22 (Phase 2) |
| G20 | Windows live connector missing | Architecture | Code Change | Low | B23 (Phase 2) |
| G21 | No secrets rotation automation | Production | Operations | Low | B24 (Phase 3) |

## 4. Gap classification rollup

| Category | Count | Of which P1 | Phase |
|----------|------:|------------:|-------|
| Configuration | 4 (G1–G3) | 3 | 1 |
| Deployment | 7 (G5–G9,G13,G16) | 4 | 1 |
| Operations | 5 (G4,G14,G15,G17,G21) | 3 | 1 / 3 |
| Testing | 3 (G10–G12) | 0 | 1 |
| Code Change | 2 (G19,G20) | 0 | 2 |
| Documentation | 1 (G18) | 0 | 1 |

## 5. Critical path to UAT

```
B06/B11 (secrets+drivers) ─┐
B08 (evidence Postgres) ───┼─► B01/B03/B04 (UAT config) ─► B12 (validate) ─► B13 (smoke) ─► UAT GO
B09 (object store) ────────┘
```

## 6. Critical path to PROD

```
UAT sign-off ─► B02/B04 (PROD config) ─► B07 (vault) ─► B10 (SSO) ─► B09/B19 (storage+TLS)
            ─► B17 (observability) ─► B18 (backup/DR) ─► B20 (sign-off) ─► PROD GO
```

## 7. Conclusion

- **No architectural blockers.** Every P1 gap to UAT is configuration, data, or
  provisioning.
- **Two code items (G19/G20)** are deferrable to Phase 2 (non-Postgres / Windows
  live connectors) and do not block UAT for the Postgres/Linux/SonarQube estate.
- **AI is ready by design**; the gap is provisioning model serving + pgvector,
  not development.
