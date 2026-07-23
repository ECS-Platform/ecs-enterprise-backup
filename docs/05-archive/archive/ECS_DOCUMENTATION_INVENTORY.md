# ECS Documentation Inventory (Phase 1)

**Audit date:** 2026-06-17 · **Method:** full repository scan (`find . -name '*.md'`), cross-checked against code and the prior `docs/05-archive/archive/DOCUMENTATION_GAP_ANALYSIS.md`, `executive/documentation_audit.md`, and the live platform. **Scope:** documentation only — no code, UI, or functionality changed.

> **Canonical metrics (computed from source — use these everywhere).** 15 frameworks · 305 controls · 702 evidence records (`framework_catalog.catalog_stats()`) · 12 connectors (`ecs_platform/connectors`) · 9 RBAC roles (`config/rbac.yaml`) · ~79 HTML screens / 66 primary nav routes · 39 test files · 10 Docker Compose services. Several older documents drift from these — flagged below.

---

## 0. Headline verdict

ECS is **document-rich** (90+ markdown artifacts) and, after the prior onboarding + product-manual work, **onboarding and product documentation are now complete**. The remaining issues are **not missing content** but **scattering, duplication, and stale counts** in older artifacts. Net new authoring required for a new engineer: **near zero** — the gaps are consolidation and correction.

| Documentation type | Status | Primary home |
|---|---|---|
| Product | ✅ Complete | `docs/product_manual/`, `product/` |
| Functional | ✅ Complete | `docs/01-product/product/ECS_USER_JOURNEYS.md`, this audit's `docs/01-product/product/ECS_FUNCTIONAL_MANUAL.md` |
| Technical | ✅ Complete | `docs/02-architecture/architecture/ecs_lld.md`, `docs/03-development/developer-manual/ECS_ENGINEERING_HANDBOOK.md` |
| Architecture | ✅ Complete | `docs/02-architecture/architecture/`, `docs/hld/`, `docs/01-product/00-start-here/ARCHITECTURE_OVERVIEW.md`, diagrams |
| Onboarding | ✅ Complete | `docs/03-development/developer-manual/DEVELOPER_SETUP_GUIDE.md`, `docs/03-development/developer-manual/ECS_ENGINEERING_HANDBOOK.md` |
| Deployment | ✅ Complete | `docs/02-architecture/architecture/ecs_deployment_architecture.md`, `docs/02-architecture/architecture/ECS_Architecture_and_Deployment_Guide.md` (partly stale) |
| Operational | ✅ Complete | `docs/03-development/operations/ecs_runbook.md`, `docs/03-development/operations/RECOVERY_RUNBOOK.md` |
| Demo | ✅ Complete | `docs/01-product/00-start-here/DEMO_MODE_SETUP.md`, `demo-data/ECS_DEMO_NARRATIVE.md`, `docs/01-product/product/ECS_DEMO_GUIDE.md` |
| Troubleshooting | ✅ Complete | `docs/01-product/00-start-here/TROUBLESHOOTING_GUIDE.md`, `docs/03-development/operations/ecs_runbook.md` |
| Knowledge transfer | ✅ Complete (this package) | `docs/TRAINING/` |

---

## 1. Full inventory (by area)

### Root
| File | Type | Status |
|---|---|---|
| `README.md` | Quick start + index | **Current** (links to docs that now exist) |
| `ECS_ARCHITECTURE_BASELINE.md` | Architecture baseline | **Outdated counts** (source of old "~307/~706") |
| `ECS_INFORMATION_ARCHITECTURE_V1.md` | Nav/IA reference | Current |

### `docs/` (engineering + onboarding)
| File | Type | Status |
|---|---|---|
| `README.md` | Doc package index | Current |
| `DEVELOPER_SETUP_GUIDE.md` | Setup (macOS/Linux/WSL) | **Current, authoritative** |
| `LOCAL_DEVELOPMENT_GUIDE.md` | Dev workflow | **Current, authoritative** |
| `ENVIRONMENT_CONFIGURATION.md` | Env var reference | **Current** (created in onboarding task) |
| `DEMO_MODE_SETUP.md` | Demo mode | **Current** (supersedes stale demo doc) |
| `COMMON_COMMANDS.md` | Command catalog | **Current** |
| `TROUBLESHOOTING_GUIDE.md` | Troubleshooting | **Current** |
| `ARCHITECTURE_OVERVIEW.md` | One-page architecture | **Current** |
| `ECS_ENGINEERING_HANDBOOK.md` | Consolidated handbook | Current |
| `ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` | Demo + troubleshooting | **STALE** (claims `.env` not loaded — false) |
| `ECS_Architecture_and_Deployment_Guide.md` | Architecture + deploy | **Partially stale** (4 deps vs 9; "no Docker") |
| `DOCUMENTATION_GAP_ANALYSIS.md` | Gap analysis | **Now partly resolved** (flagged docs were since created) |
| `ECS_DEPENDENCY_REPORT.md` / `ECS_MODULE_OWNERSHIP.md` | Coupling / ownership | Current (analysis/proposal) |
| `ECS_MIGRATION_REPORT.md` / `ECS_REFACTOR_PLAN.md` / `ECS_ROLLBACK_REPORT.md` / `ECS_RBAC_LEGACY_FLAWS.md` | Refactor/RBAC history | Current (historical) |
| `RECOVERY_RUNBOOK.md` | Backup/restore | **Current, authoritative** |
| `architecture/ecs_enterprise_architecture_review.md` | EA review | Current |
| `architecture/ecs_deployment_architecture.md` | Deployment arch | Current |
| `hld/ecs_hld.md` · `lld/ecs_lld.md` | HLD / LLD | Current |
| `diagrams/ecs_er_diagrams.md` · `diagrams/ecs_sequence_diagrams.md` | Diagrams | Current |
| `executive/ecs_technology_dossier.md` | Exec dossier | Current |
| `operations/ecs_runbook.md` | Ops runbook | Current |
| `product_manual/*` (8 files) | Product Operations Manual | **Current, authoritative** |

### `docs/product_manual/` (8 docs + 66 screenshots) — the authoritative product reference
`ECS_PRODUCT_MANUAL.md`, `ECS_MODULE_REFERENCE.md`, `ECS_PERSONA_GUIDE.md`, `ECS_SCREEN_CATALOG.md`, `ECS_KPI_DICTIONARY.md`, `ECS_FEATURE_REFERENCE.md`, `ECS_USER_JOURNEYS.md`, `ECS_SCREENSHOTS_INDEX.md`.

### Executive / strategy / product / UX (non-engineering)
- `executive/` (7): board summary, demo story, master index, ROI, readiness package, pitch deck, `documentation_audit.md` (prior consistency audit).
- `product/` (4): `ecs_product_assessment.md`, `ecs_enterprise_backlog.md`, `enterprise_feature_backlog.md`, `product_maturity_assessment.md`.
- `strategy/` (5): competitive analysis, 3-year strategy, ROI model, market positioning, ADIP convergence.
- `roadmap/` (1): `ecs_3_year_product_roadmap.md`.
- `presales/` (1): customer pitch. `ux/` (2): UX assessment + modernization review.
- `architecture/` (root, 1): **duplicate** of `docs/02-architecture/architecture/ecs_enterprise_architecture_review.md`.

### `nav_audit/` (≈50 validation reports) — prior QA evidence
Route audits (`route_audit_report.md`, `broken_routes.md`, `dead_link_report.md`), demo readiness (`final_demo_readiness_report.md`, `missing_mock_data_audit.md`, `mock_data_coverage_report.md`, `demo_mode_validation.md`), drilldown validation (8 files), persona validation, executive KPI catalog, UI/theme/accessibility audits, and hotfix verifications. **Valuable but uses older demo counts** (see contradictions).

### `reports/` & module reports
`modules/enterprise_grc/reports/APP_OWNER_CERTIFICATION_SUMMARY.md` and `reports/` (2 entries) — generated sample artifacts.

---

## 2. Missing documents

After the onboarding + product-manual work, **no critical document is missing**. Minor/optional gaps:

| # | Item | Severity | Note |
|---|---|---|---|
| M1 | Formal **release/tagging process** doc | Low | Branching exists only as a *proposal* in `ECS_MODULE_OWNERSHIP.md` |
| M2 | **API reference** (the `/api/*` JSON surface) as a standalone doc | Low | Endpoints are catalogued in `ECS_FEATURE_REFERENCE.md` but not as an OpenAPI/reference doc |
| M3 | **CONTRIBUTING.md / CODEOWNERS** | Low | Ownership is in `ECS_MODULE_OWNERSHIP.md` but not in standard GitHub files |
| M4 | **Security/secrets handling** runbook (vault, rotation) | Low | Mentioned in maturity assessment as a target |

---

## 3. Duplicate documents

| # | Duplication | Files | Resolution |
|---|---|---|---|
| D1 | EA review duplicated | root `architecture/ecs_enterprise_architecture_review.md` vs `docs/02-architecture/architecture/…` | Keep `docs/` copy; retire root stray |
| D2 | Setup instructions in 3 places | `README.md`, `DEVELOPER_SETUP_GUIDE.md`, `ECS_Architecture_and_Deployment_Guide.md §13` | Keep README (quick) + setup guide (deep); demote Arch-Guide §13 |
| D3 | Demo-mode guidance in 2 places | `docs/01-product/00-start-here/DEMO_MODE_SETUP.md` (current) vs `ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` (stale) | Keep new; banner the old |
| D4 | KPI dictionary in 2 places | `docs/01-product/product/PRODUCT_MANUAL_ECS_KPI_DICTIONARY.md`, `nav_audit/executive_kpi_catalog.md`, and this audit's `docs/05-archive/archive/AUDIT_ECS_KPI_DICTIONARY.md` + `docs/01-product/product/ECS_KPI_REFERENCE.md` | Product-manual version is the technical source; AUDIT/TRAINING versions are audience-tailored views |
| D5 | Backlog duplicated | `product/ecs_enterprise_backlog.md` vs `product/enterprise_feature_backlog.md` | Consolidate; treat enterprise_backlog as canonical |
| D6 | ROI model duplicated | `executive/ecs_roi_model.md` vs `strategy/ecs_roi_model.md` | Per documentation_audit.md — pending finance sign-off |

---

## 4. Outdated documents

| # | File | Issue | Correct value |
|---|---|---|---|
| O1 | `ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` | Claims `.env` not loaded | `.env` **is** loaded (`app/env_bootstrap.py`) |
| O2 | `ECS_Architecture_and_Deployment_Guide.md` | "4 dependencies", "no Docker" | 9 deps (`requirements.txt`); 10-service Docker stack |
| O3 | `ECS_ARCHITECTURE_BASELINE.md` | "~307 controls / ~706 evidence" | 305 / 702 |
| O4 | `product/product_maturity_assessment.md` | "20 frameworks" | 15 (catalog) |
| O5 | `nav_audit/final_demo_readiness_report.md` | "17 frameworks, 320 controls, 1,200 evidence, 10 connectors" | Catalog: 15/305/702/12 (demo-seed runtime numbers differ; see contradictions) |
| O6 | `DOCUMENTATION_GAP_ANALYSIS.md` | Lists 5 onboarding docs as "not created" | They **now exist** (created in onboarding task) |

---

## 5. Contradictory documents

| # | Topic | Conflicting values | Authoritative source |
|---|---|---|---|
| C1 | **Framework count** | 15 (`framework_catalog`) vs 17 (demo readiness) vs 20 (maturity) | **15** — `catalog_stats()` |
| C2 | **Control count** | 305 (catalog) vs 320 (demo readiness) vs ~307 (baseline) | **305** |
| C3 | **Evidence count** | 702 (catalog) vs 1,200 (demo readiness) | **702** in catalog; demo seed generates more at runtime — *both can be true*; documents must say which |
| C4 | **Connector count** | 12 (`connectors/`) vs 10 (demo readiness) vs 13 (older docs) | **12** |
| C5 | **`.env` loading** | "not loaded" vs "loaded" | **Loaded** |
| C6 | **Test count** | 38 vs 39 vs "23+" | **39** (`ls tests/test_*.py`) |

> **Root cause of C1–C4:** the `nav_audit` demo reports and `product_maturity_assessment.md` count **demo-seed runtime datasets** (which are larger/rounded for presentation) while the catalog reflects the **static framework library**. This is a real product behavior, not an error — but documents must explicitly state *catalog vs demo-seed* to stop the drift.

---

## 6. Incomplete documents

| # | File | Incompleteness |
|---|---|---|
| I1 | `ECS_Architecture_and_Deployment_Guide.md` | As-built sections predate Docker/dotenv; needs the "target" half updated |
| I2 | `ECS_MODULE_OWNERSHIP.md` | Branching/PR rules are a *proposal*, not the enforced process |
| I3 | `DOCUMENTATION_GAP_ANALYSIS.md` | Self-superseded; should be marked "resolved 2026-06-16" |

---

## 7. Recommendations (documentation-only; no code change)

1. **Standardize counts** to the canonical metrics box above; add a one-line "catalog vs demo-seed" note wherever counts appear.
2. **Banner the stale docs** (O1, O2) pointing to their current replacements.
3. **Retire the root EA-review duplicate** (D1) once references repoint.
4. **Mark `DOCUMENTATION_GAP_ANALYSIS.md` resolved** (I3) — its flagged docs now exist.
5. **Add a thin release-process doc** (M1) and standard `CONTRIBUTING.md`/`CODEOWNERS` (M3).
6. Treat `docs/product_manual/` + this `docs/AUDIT/` + `docs/TRAINING/` as the **single source of truth** going forward.

**Conclusion:** Documentation **coverage is sufficient** for a new engineer; the work needed is **hygiene (counts, banners, de-duplication)**, not authoring.
