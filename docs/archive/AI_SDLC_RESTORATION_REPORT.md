# ECS AI SDLC — Restoration & Demo-Enablement Report

**Branch:** `cursor/predefined-queries-module`
**Base commit at time of work:** `7003446` (`feat: add 16k input 1k output token validation benchmark`)
**Change type:** Additive, UI-only (single navigation partial). No routes, services, engines, or benchmark files modified.
**Purpose:** Restore/enable the ECS-native **AI SDLC** module in the left navigation for the CIO/MD senior-management demo, safely and additively.

---

## 1. Executive summary

The ECS-native AI SDLC module was **already present and fully wired** on this branch. Both recovered source commits are ancestors of the current `HEAD`, so their content was already merged into the working tree:

| Recovered commit | Message | Relationship to HEAD |
|---|---|---|
| `0b29018` | ECS module refactor and AI SDLC enhancements | **Ancestor of HEAD** — modular `modules/ai_sdlc/` structure already in tree |
| `15fa0ed` | AI SDLC Control Tower checkpoint | **Ancestor of HEAD** — original ECS-native engines/templates already in tree |
| `825b073` | ADIP AI SDLC analysis workflows | **NOT restored** (ADIP-specific; conceptual reference only, per instruction) |

Concretely, the following were verified to already exist and function:
- **13 engines** under `modules/ai_sdlc/engines/` (Control Tower, onboarding, workflow, reports, governance service, stage dashboard, controlled documents, knowledge repository, evidence governance, drilldowns).
- **Route registration** in `app/main.py` via `register_ai_sdlc_routes(app, templates)` (line ~1523–1525) — 14 page routes + ~20 API routes.
- **23 templates** (12 pages + 11 partials) under `modules/ai_sdlc/templates/`.
- **Backward-compatible shims** in `app/` (e.g. `app/routes_ai_sdlc_governance.py`, `app/ai_sdlc_*.py`) re-exporting from the modular package.
- **6 AI SDLC test files** under `tests/`.
- A ready-made left-nav partial `modules/shared/templates/partials/ecs_nav_ai_sdlc.html` with the AI SDLC group and all sub-tabs.

**The one gap:** during the earlier Phase 1 Information-Architecture refactor, the AI SDLC navigation group was placed inside a `{% if show_phase2_nav %}` block that defaults to `false`. As a result the AI SDLC group — although all its pages were live and URL-reachable — **did not appear in the left sidebar** on the dashboards.

**The fix (this change):** surface the existing AI SDLC nav group as a first-class, always-visible left-nav group by moving the `{% include "partials/ecs_nav_ai_sdlc.html" %}` line out of the hidden Phase 2 block. The other Phase 2 sections (Executive extras, Frameworks list, Enterprise GRC) remain hidden, preserving the Phase 1 IA refactor's intent. This is a **single-file, ~14-line UI change**.

---

## 2. Required demo capabilities — coverage

All required sub-tabs/stages are present in the left-nav AI SDLC group (`ecs_nav_ai_sdlc.html`) and render with deterministic mock/demo data:

| Required stage / capability | Route | Nav label |
|---|---|---|
| Overview / Control Tower | `/mvp/ai-sdlc`, `/mvp/ai-sdlc/control-tower` | Home, AI SDLC Control Tower |
| Requirements (Control Requirement Documents) | `/mvp/ai-sdlc/requirements` | Requirements |
| Design / Architecture (Control Design Documents) | `/mvp/ai-sdlc/design` | Design |
| Development (implementation checklist/artifacts) | `/mvp/ai-sdlc/development` | Development |
| Testing (control test cases / validation) | `/mvp/ai-sdlc/testing` | Testing |
| Go-Live / Release (readiness checklist) | `/mvp/ai-sdlc/golive` | Go-Live |
| Documents / Artifacts (clickable documents) | `/mvp/ai-sdlc/evidence`, `/api/ai-sdlc/controlled-document` | Evidence Collection |
| Reports / Worklist (stage-wise pending & status) | `/mvp/ai-sdlc/reports`, `/mvp/ai-sdlc/findings` | Reports, Findings & Remediation |
| Application onboarding / select or view an application | `/mvp/ai-sdlc/onboarding` | Application Onboarding |

Functional demo behaviors backed by existing engines (all mock/demo data, no live LLM calls):
- Select/view an application and see **applicable controls** and **missing controls** (control-tower + onboarding engines / drills).
- For a new application concept, **generate/select applicable controls** using demo data (onboarding run).
- **Generated Control Requirement / Control Design documents** surfaced as cards/links (controlled-document API + stage dashboards).
- **Implementation, testing, and go-live checklists** per stage (`ecs_sdlc_stage_dashboard.py` sections: BRD/FRD, Solution/Technical Architecture, HLD/LLD, Code Repositories, SAST, Test Cases, SIT/UAT, release readiness).
- **Clickable generated documents** (evidence viewer) and **stage-wise pending actions/status** (worklist/reports).

---

## 3. Files

### 3.1 Modified (this change)
| File | Change |
|---|---|
| `modules/shared/templates/partials/ecs_nav_groups.html` | Moved the AI SDLC nav include (`partials/ecs_nav_ai_sdlc.html`) out of the hidden `{% if show_phase2_nav %}` block and made it a first-class always-visible group (Group 5). Replaced the in-Phase-2 include with a comment to avoid double-render when `show_phase2_nav=True`. **No routes/services/APIs changed.** |

### 3.2 Restored / adapted
**None required.** All AI SDLC source, routes, templates, and tests were already present in the working tree (inherited from ancestor commits `0b29018` and `15fa0ed`) and already adapted to the current modular layout (`modules/ai_sdlc/…`). No files were copied from history and no imports needed adaptation. Verified by:
- `python -m compileall app modules scripts` → clean (exit 0).
- Live route rendering (see §4).

### 3.3 Added
| File | Purpose |
|---|---|
| `docs/archive/AI_SDLC_RESTORATION_REPORT.md` | This report. |

### 3.4 Pre-existing AI SDLC assets (verified present, unchanged)
- **Engines** (`modules/ai_sdlc/engines/`): `ai_sdlc_control_tower_engine.py`, `ai_sdlc_controlled_documents.py`, `ai_sdlc_document_artifacts.py`, `ai_sdlc_evidence_governance.py`, `ai_sdlc_governance_mock.py`, `ai_sdlc_governance_service.py`, `ai_sdlc_knowledge_repository.py`, `ai_sdlc_onboarding_engine.py`, `ai_sdlc_reports_engine.py`, `ai_sdlc_workflow_engine.py`, `ai_sdlc_workflow_store.py`, `ecs_ai_governance_drilldowns.py`, `ecs_sdlc_stage_dashboard.py`.
- **Routes** (`modules/ai_sdlc/routes/`): `routes_ai_sdlc_governance.py` (registered in `app/main.py`).
- **Templates** (`modules/ai_sdlc/templates/`): 12 page templates + 11 partials (Control Tower, home, onboarding, worklist, reports, report detail, evidence viewer, governance quality, SDLC gates, AI governance posture, AI registry, plus stage/workflow partials).
- **Nav partial**: `modules/shared/templates/partials/ecs_nav_ai_sdlc.html`.
- **Compat shims** (`app/`): `routes_ai_sdlc_governance.py`, `ai_sdlc_control_tower_engine.py`, `ai_sdlc_controlled_documents.py`, `ai_sdlc_document_artifacts.py`, `ai_sdlc_governance_mock.py`, `ai_sdlc_governance_service.py`, `ai_sdlc_knowledge_repository.py`, `ai_sdlc_onboarding_engine.py`, `ai_sdlc_reports_engine.py`, `ai_sdlc_workflow_engine.py`, `ai_sdlc_workflow_store.py`, `ecs_sdlc_stage_dashboard.py`.
- **Tests** (`tests/`): `test_ai_sdlc_control_tower.py`, `test_ai_sdlc_controlled_documents.py`, `test_ai_sdlc_governance_corrections.py`, `test_ai_sdlc_onboarding.py`, `test_ai_sdlc_redesign.py`, `test_ai_sdlc_workflow.py`.

---

## 4. Routes added / registered

No new routes were added. The AI SDLC routes were already registered in `app/main.py`:

```python
from app.routes_ai_sdlc_governance import register_ai_sdlc_routes
register_ai_sdlc_routes(app, templates)
```

### Page routes (open in browser; append `?role=cio&user=CIO`)
- `/mvp/ai-sdlc` — AI SDLC home / Overview
- `/mvp/ai-sdlc/control-tower` — Control Tower
- `/mvp/ai-sdlc/onboarding` — Application Onboarding
- `/mvp/ai-sdlc/requirements` — Requirements
- `/mvp/ai-sdlc/design` — Design / Architecture
- `/mvp/ai-sdlc/development` — Development
- `/mvp/ai-sdlc/testing` — Testing
- `/mvp/ai-sdlc/golive` — Go-Live / Release
- `/mvp/ai-sdlc/evidence` — Documents / Artifacts (Evidence Collection)
- `/mvp/ai-sdlc/findings` — Findings & Remediation
- `/mvp/ai-sdlc/reports` — Reports / Worklist
- `/mvp/ai-governance` — AI Governance Posture
- `/mvp/ai-registry` — AI Registry
- `/mvp/governance-quality` — Governance Quality

### Representative API routes (JSON, mock data)
- `/api/ai-sdlc/posture`, `/api/ai-sdlc/registry`, `/api/ai-sdlc/sdlc`
- `/api/ai-sdlc/controlled-document`, `/api/ai-sdlc/controlled-document/counts`
- `/api/ai-sdlc/control-tower/tab/{tab_id}`, `/api/ai-sdlc/control-tower/drill/*`
- `/api/ai-sdlc/onboarding/run`, `/api/ai-sdlc/onboarding/drill/*`
- `/api/ai-sdlc/workflow/review`, `/api/ai-sdlc/workflow/action` (POST)
- `/api/ai-sdlc/governance-quality`, `/api/ai-sdlc/governance-scan`

---

## 5. Navigation changes

- The left sidebar (single source: `mvp_sidebar.html` → `ecs_sidebar.html` → `ecs_nav_groups.html`) now shows a first-class, always-visible **"AI SDLC Governance"** group across all dashboards and MVP pages.
- Group contents (from `ecs_nav_ai_sdlc.html`): **Home, AI SDLC Control Tower, Application Onboarding, Requirements, Design, Development, Testing, Go-Live, Evidence Collection, Findings & Remediation, Reports**.
- The Phase 1 IA refactor is otherwise preserved: Executive extras, the per-framework list, and Enterprise GRC remain behind `show_phase2_nav` (default `false`).

---

## 6. Validation commands & results

Run with demo mode on (auth bypassed for the demo, exactly as the app runs for CIO/MD):
`DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off`

| Check | Command | Result |
|---|---|---|
| Syntax / compile | `python -m compileall app modules scripts` | **PASS** (exit 0) |
| Full demo readiness (regression) | `python scripts/validate_demo_readiness.py` | **READY — 45 screens, 0 defects (P1=0, P2=0, P3=0)** |
| AI SDLC smoke test (pages + APIs + nav) | TestClient smoke over 14 pages, 6 APIs, 5 core pages, nav presence on 3 pages | **28/28 checks PASS** |
| AI SDLC unit/integration tests | `pytest tests/test_ai_sdlc_*.py` | **59 passed, 2 failed** |

**The 2 failing tests are pre-existing and unrelated to this change** — they fail identically on the original (pre-change) code (verified by re-running after `git stash` of the nav change):
- `tests/test_ai_sdlc_redesign.py::test_sidebar_new_menu_only` — asserts a string absent from the sidebar, but the string (`AI Governance Posture`) appears in an unrelated in-page JavaScript drill-footer helper.
- `tests/test_ai_sdlc_redesign.py::test_onboarding_execution_workspace` — asserts onboarding page body text (`Discover applications`) that the current onboarding template does not contain.

Both are stale content assertions in the test file; neither concerns the left navigation. They were not introduced by, and are not affected by, this change.

**Smoke test — left-nav verification (post-change):**
```
[4] Left-nav AI SDLC group present on main pages (nav toggle + all stage links):
  [PASS] group=True  stage_links=8/8  /dashboard/cio
  [PASS] group=True  stage_links=8/8  /dashboard?role=owner&user=AppOwner
  [PASS] group=True  stage_links=8/8  /mvp/ai-sdlc
```

Live-server checks additionally confirmed HTTP 200 for the AI SDLC home, Control Tower, and CIO dashboard, with the `nav-ai-sdlc` group and all stage links rendered in the sidebar.

> Note: `fastapi`/`uvicorn`/`jinja2` were installed only in a throwaway virtualenv at `/tmp` for validation (the same demo deps `start_ecs.sh` installs, all already declared in `requirements.txt`). No new dependency was added to the repo, and the system Python was not modified.

---

## 7. Benchmark & Phase 1 safety confirmation

`git status` after the change shows **exactly one modified file** (`modules/shared/templates/partials/ecs_nav_groups.html`). The following protected paths were verified **untouched** (`git status --short` empty for each; files still present):
- `scripts/run_neev_validation_benchmark.py` ✔ untouched
- `scripts/run_16k_1k_token_validation.py` ✔ untouched
- `benchmarks/ai_workload/*` ✔ untouched
- `docs/benchmarks/*` ✔ untouched
- Phase 1 evidence-collection modules, existing routes, and templates ✔ untouched (no deletions; only the single nav partial edited)

---

## 8. Known limitations

- **Demo data only.** All AI SDLC figures, documents, controls, findings, and readiness values are deterministic mock/demo data from the historical engines. No live LLM calls are made by this module.
- **Auth for demo.** The AI SDLC pages (like the rest of ECS) render token-free only when `DEMO_MODE=true`. With `ECS_AUTH_ENABLED=true` and `DEMO_MODE=false` (the current `.env`), routes require a valid token and return 401 — expected. For the CIO/MD demo, run with `DEMO_MODE=true` (as `start_ecs.sh`/`docker-compose` do for the demo profile). The repo `.env` was intentionally **not** modified.
- **Two pre-existing test assertions** in `tests/test_ai_sdlc_redesign.py` are stale (see §6). They are out of scope for this navigation restoration; fixing them would require editing test expectations or onboarding page copy and is left for a follow-up.
- **Nav placement.** AI SDLC is surfaced as a top-level sidebar group (not nested under an existing group), matching the historical `ecs_nav_ai_sdlc.html` design and the "left navigation item" requirement.

---

## 9. Next steps (optional)

1. If AI SDLC should be visible only for specific roles (e.g. CIO / AI Governance Owner), wrap the Group-5 include in a role check in `ecs_nav_groups.html`.
2. Update or retire the two stale assertions in `tests/test_ai_sdlc_redesign.py` to reflect the current onboarding template and sidebar.
3. If desired for production, gate the group behind a dedicated flag (e.g. `show_ai_sdlc_nav`) instead of always-on, mirroring the `show_phase2_nav` pattern.
