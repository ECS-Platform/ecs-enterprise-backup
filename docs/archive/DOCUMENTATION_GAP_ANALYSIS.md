# ECS — Documentation Gap Analysis

**Date:** 2026-06-16
**Method:** Direct review of every documentation artifact in the repository, cross-checked
against the live code (`requirements.txt`, `app/env_bootstrap.py`, `app/main.py`,
`docker-compose.yml`, `tests/`, `config/`). All counts below are computed from source, not
copied from prior documents.
**Question answered:** *Does a complete new-engineer onboarding guide already exist?*

## TL;DR

**No single complete onboarding guide exists.** Onboarding content is **strong but scattered
across 5+ documents**, the root `README.md` **links to 5 onboarding documents that were never
created**, and the oldest demo-mode guide is **factually stale** (it claims ECS does not load
`.env`, which is false). The fix is consolidation, not net-new authoring: this analysis is paired
with a new authoritative [`docs/developer-manual/ECS_ENGINEERING_HANDBOOK.md`](../developer-manual/ECS_ENGINEERING_HANDBOOK.md) that
unifies the accurate material and supersedes the scattered/stale pieces.

---

## 0. Inventory (what actually exists)

| Path | Type | Status | Notes |
|---|---|---|---|
| `README.md` | Quick start + index | **Current** | Accurate; but links to 5 non-existent docs (see §6). |
| `docs/README.md` | Doc package index | Current | Indexes the architecture package (#1–#8). |
| `docs/developer-manual/DEVELOPER_SETUP_GUIDE.md` | Setup (macOS/Linux/WSL) | **Current, authoritative** | Best setup doc; matches code. |
| `docs/developer-manual/LOCAL_DEVELOPMENT_GUIDE.md` | Dev workflow | **Current, authoritative** | Best workflow doc; matches code. |
| `docs/00-start-here/ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` | Demo mode + troubleshooting | **STALE / partially incorrect** | Claims `.env` is not loaded — false (see §5, §7). |
| `docs/architecture/ECS_Architecture_and_Deployment_Guide.md` | Architecture + deploy | **Partially stale** | States 4 deps (actual 9), "no Docker", "no .env" — predates Docker stack & dotenv. |
| `docs/developer-manual/ECS_DEPENDENCY_REPORT.md` | Cross-module coupling | Current (analysis) | Refactor-oriented; not onboarding. |
| `docs/developer-manual/ECS_MODULE_OWNERSHIP.md` | Ownership + branch/PR rules | Current (proposal) | Only place with branching/PR guidance (recommended, not enforced). |
| `docs/operations/RECOVERY_RUNBOOK.md` | Backup/restore/migration | **Current, authoritative** | Accurate, scoped to Postgres repository. |
| `docs/archive/ECS_MIGRATION_REPORT.md` | Refactor history | Current (historical) | Background only. |
| `docs/developer-manual/ECS_REFACTOR_PLAN.md` | Refactor plan | Current (historical) | Background only. |
| `docs/developer-manual/ECS_RBAC_LEGACY_FLAWS.md` | RBAC analysis | Current (historical) | Background only. |
| `docs/archive/ECS_ROLLBACK_REPORT.md` | Rollback history | Current (historical) | Background only. |
| `docs/architecture/ecs_enterprise_architecture_review.md` | EA review | Current | Architecture package #1. |
| `docs/architecture/ecs_deployment_architecture.md` | Deployment arch | Current | Architecture package #6. |
| `docs/architecture/ecs_hld.md` | HLD | Current | Architecture package #2. |
| `docs/architecture/ecs_lld.md` | LLD | Current | Architecture package #3. |
| `docs/diagrams/ecs_er_diagrams.md` | ER diagrams | Current | Architecture package #4. |
| `docs/diagrams/ecs_sequence_diagrams.md` | Sequences | Current | Architecture package #5. |
| `docs/archive/ecs_technology_dossier.md` | Exec dossier | Current | Architecture package #7. |
| `docs/operations/ecs_runbook.md` | Ops runbook | Current | Architecture package #8 (operational troubleshooting). |
| `executive/*` (7 files) | Exec/board/ROI/pitch | Current | Non-engineering; `documentation_audit.md` is a prior consistency audit. |
| `architecture/ecs_enterprise_architecture_review.md` (root) | EA review | **Duplicate** | Same title as `docs/architecture/...`; root copy is the stray. |
| `ECS_ARCHITECTURE_BASELINE.md` (root) | Baseline | Partially stale | Source of the old "~307/~706" counts (now 305/702). |
| `ECS_INFORMATION_ARCHITECTURE_V1.md` (root) | IA | Current | Nav/IA reference. |

> The directories named in the request — root `architecture/`, `executive/`, `hld/`, `lld/` —
> mostly resolve **under `docs/`**. Root `hld/` and `lld/` are empty; root `architecture/` holds a
> single duplicate file; root `executive/` holds the executive (non-engineering) deck content.

---

## 1. Existing setup documentation

| Topic | Where | Verdict |
|---|---|---|
| New-engineer setup (macOS/Linux/Windows-WSL) | `docs/developer-manual/DEVELOPER_SETUP_GUIDE.md` | **Complete & accurate.** Per-OS prerequisites, venv, deps, `.env`, health check, post-setup checklist. |
| Fastest demo start | `README.md` §"Fastest start" | Accurate. |
| Full Docker stack | `README.md`, `DEVELOPER_SETUP_GUIDE.md` §4 | Accurate; matches `docker-compose.yml` (10 services). |
| As-built setup (legacy) | `docs/architecture/ECS_Architecture_and_Deployment_Guide.md` §13 | **Stale** — says 4 deps, "no Docker", uses `.venv`/`wkin_ecs_consolidated_demo_v13`. |

**Gap:** Two setup narratives disagree on dependency count and Docker availability. The Architecture
& Deployment Guide predates the Docker stack and the 9-package `requirements.txt`.

## 2. Existing environment configuration documentation

| Topic | Where | Verdict |
|---|---|---|
| Env var table (full) | **Missing** — `README.md` links to `docs/developer-manual/ENVIRONMENT_CONFIGURATION.md` which **does not exist**. | **Gap.** |
| Authoritative template | `.env.example` (10 KB, secure-by-default) | Exists in repo; not summarized in any doc. |
| Key flags (`DEMO_MODE`, `ECS_AUTH_ENABLED`) | Setup/Local guides mention the two flags | Partial — only 2 of dozens documented. |
| Backup/repository vars | `docs/operations/RECOVERY_RUNBOOK.md` §0 | Complete for repository vars. |

**Gap:** No consolidated environment-variable reference. `.env.example` is the de-facto source of
truth but has no companion doc. Defaults are **secure-by-default** (`ECS_AUTH_ENABLED=true`,
`DEMO_MODE=false`) — a fact not stated anywhere in onboarding docs.

## 3. Existing demo-mode documentation

| Topic | Where | Verdict |
|---|---|---|
| Demo-mode purpose & flags | `docs/00-start-here/ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` | **Stale** — see §5/§7. Correct on *which* flags; wrong on *how env is loaded*. |
| Demo start (accurate) | `README.md`, `DEVELOPER_SETUP_GUIDE.md` §1.4 | Accurate (`cp .env.example .env`, set flags). |
| Demo data lifecycle | `LOCAL_DEVELOPMENT_GUIDE.md` §7 | Accurate. |
| Canonical demo-mode doc | `README.md` links to `docs/00-start-here/DEMO_MODE_SETUP.md` which **does not exist** | **Gap.** |

**Gap:** The only dedicated demo-mode document is the stale one; the accurate demo instructions are
spread across README and the setup guide.

## 4. Existing architecture documentation

**Strong and largely current.** Full package under `docs/`:
EA review, HLD, LLD, ER diagrams, sequence diagrams, deployment architecture, technology dossier,
operations runbook (indexed by `docs/README.md`).

| Caveat | Detail |
|---|---|
| `docs/architecture/ECS_Architecture_and_Deployment_Guide.md` | Useful as-built/target comparison, but stale on deps/Docker/env. |
| `README.md` links `docs/00-start-here/ARCHITECTURE_OVERVIEW.md` | **Does not exist** — the short engineer-facing overview is missing (the full package exists, but no one-page entry). |
| Root `architecture/...` | Duplicate of `docs/architecture/...`. |

## 5. Existing troubleshooting documentation

| Topic | Where | Verdict |
|---|---|---|
| Demo-mode 401 / env not visible | `docs/00-start-here/ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` | **Partially obsolete.** Symptom is real; stated root cause ("no dotenv") is wrong for the current build. |
| As-built symptom table | `docs/architecture/ECS_Architecture_and_Deployment_Guide.md` §19 | Useful, generic. |
| Operational troubleshooting | `docs/operations/ecs_runbook.md` | Current. |
| Setup-failure pointer | `DEVELOPER_SETUP_GUIDE.md` → links `docs/00-start-here/TROUBLESHOOTING_GUIDE.md` which **does not exist** | **Gap.** |

## 6. Missing onboarding content

Items a new engineer needs that have **no current home** (or only a broken link):

1. **Single onboarding entry point / "Day 1" path.** Content exists but is fragmented across 4–5 files.
2. **`docs/developer-manual/ENVIRONMENT_CONFIGURATION.md`** — linked by README, **not created**. No full env-var reference.
3. **`docs/00-start-here/DEMO_MODE_SETUP.md`** — linked by README, **not created**.
4. **`docs/00-start-here/COMMON_COMMANDS.md`** — linked by README, **not created**. No command catalog (start/stop/test/seed/backup).
5. **`docs/00-start-here/TROUBLESHOOTING_GUIDE.md`** — linked by README & setup guide, **not created**.
6. **`docs/00-start-here/ARCHITECTURE_OVERVIEW.md`** — linked by README, **not created** (the deep package exists, the one-pager doesn't).
7. **Branching strategy (authoritative).** Only *recommendations* in `ECS_MODULE_OWNERSHIP.md`; no doc reflects the actual `main` + `cursor/*` workflow in use.
8. **Release process.** **No document exists** for tagging/release/promotion.
9. **Developer workflow as one narrative** — inner loop, tests, validators, template checks (exists in `LOCAL_DEVELOPMENT_GUIDE.md` but not tied into a handbook).
10. **Accurate dependency list in prose** — `requirements.txt` has 9 packages; the Architecture Guide says 4.

## 7. Duplicate / conflicting documentation

| # | Duplication / conflict | Files | Resolution |
|---|---|---|---|
| D1 | **`.env` loading** — "not loaded / no `load_dotenv()`" vs "loaded at startup via python-dotenv" | `ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` ❌ vs `LOCAL_DEVELOPMENT_GUIDE.md` ✅ + `app/env_bootstrap.py`/`requirements.txt` | **Code wins:** `.env` **is** loaded. Mark the demo-mode doc superseded. |
| D2 | **Dependency count** — 4 vs 9 | `ECS_Architecture_and_Deployment_Guide.md` (4) vs `requirements.txt` (9) | 9 is correct. |
| D3 | **Docker** — "not present in repository" vs full 10-service stack | `ECS_Architecture_and_Deployment_Guide.md` §15 vs `docker-compose.yml` | Docker stack exists. |
| D4 | **Setup duplicated** three times | README, `DEVELOPER_SETUP_GUIDE.md`, `ECS_Architecture_and_Deployment_Guide.md` §13 | Keep README (quick) + setup guide (deep); demote Arch-Guide §13. |
| D5 | **EA review duplicated** | root `architecture/...` vs `docs/architecture/...` | Keep `docs/` copy; retire root stray. |
| D6 | **Counts drift** (frameworks 15/16, controls 305/307, tests 38/39/"23+") | multiple | Use computed values: **15 frameworks, 305 controls, 702 evidence, 12 connectors, 9 RBAC roles, 10 Docker services, 39 test files** (per `executive/documentation_audit.md` + current `ls tests/*.py`). |
| D7 | **Branch/PR rules** appear only as a proposal | `ECS_MODULE_OWNERSHIP.md` §5 | Promote an accurate, current branching section into the handbook. |

## 8. Recommended consolidation plan

**Principle:** consolidate and supersede; do not duplicate. Reuse the accurate guides verbatim by
reference; quarantine the stale ones.

1. **Create one authoritative source:** [`docs/developer-manual/ECS_ENGINEERING_HANDBOOK.md`](../developer-manual/ECS_ENGINEERING_HANDBOOK.md)
   (done in this change) covering setup → onboarding → environment → architecture → demo mode →
   troubleshooting → commands → branching → release → developer workflow.
2. **Designate authoritative children** the handbook links to (no rewrite needed):
   `DEVELOPER_SETUP_GUIDE.md`, `LOCAL_DEVELOPMENT_GUIDE.md`, `RECOVERY_RUNBOOK.md`, and the
   `docs/` architecture package (`docs/README.md`).
3. **Fix the README's broken links:** point the 5 missing-doc links to the relevant handbook
   sections (or create thin redirect stubs). *(Recommended follow-up; not auto-applied to avoid
   churn beyond the requested deliverables.)*
4. **Supersede the stale demo-mode doc:** add a banner to
   `ECS_DEMO_MODE_SETUP_AND_TROUBLESHOOTING.md` pointing to the handbook and correcting D1.
   *(Recommended; the handbook already documents the correct behavior.)*
5. **Demote the Architecture & Deployment Guide's setup/deps/env sections** (§13, §15–§17) in favor
   of the handbook; keep its as-built-vs-target comparison.
6. **Retire the root EA-review duplicate** (D5) once references are repointed.
7. **Standardize counts** to the computed values (D6) wherever docs are next edited; treat
   `executive/ecs_master_index.md` + this analysis as the metric source of truth.

**Net authoring required:** ~0 net-new concepts — everything is consolidation of existing,
verified material into the handbook plus correction of the four stale facts (D1–D3, D6).
