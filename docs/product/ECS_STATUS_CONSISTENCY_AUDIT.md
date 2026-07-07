# ECS Status Consistency Audit

**Scope:** Every status string surfaced across Predefined Queries, Evidence Explorer, Dashboard KPIs, Framework KPIs, Query Execution, and the Evidence Workflow.
**Goal:** Displayed status must equal runtime reality. No misleading or contradictory states.
**Source of truth (code):** `modules/operations/engines/predefined_queries_engine.py` (`assess_execution_capability`), `modules/operations/engines/resubmission.py`, `modules/shared/services/*`.

> **Fixed in this pass** issues are marked ✅ FIXED with the change applied. Items marked ⚠️ are content/runtime caveats documented for awareness (no code defect).

## Predefined Queries — execution status

| Status | Displayed Location | Backend Source | Actual Logic (after fix) | Expected Meaning | Issue Found | Recommended Fix |
|---|---|---|---|---|---|---|
| **Ready** | Catalog status badge, Detail Summary tab | `assess_execution_capability()` | predefined **AND** known technology **AND** implemented connector **AND** in `LIVE_CONTROL_IDS` **AND** dependency present | Control is genuinely executable now | **Y (was)** — previously "Ready" = predefined + known tech only (16 controls), regardless of executability | ✅ FIXED — "Ready" now requires real executable capability (6 controls) |
| **Manual** | Catalog / Detail | `assess_execution_capability()` | `predefined == False` | No predefined query; manual evidence collection | N | — (0 manual in current library) |
| **Unsupported Technology** | Catalog / Detail / KPI drilldown | `detect_technology()` → `Unknown` | predefined but query matched no `TECHNOLOGY_RULES` pattern | Query cannot be auto-classified to a connector | N | Already accurate (21 controls) |
| **Connector Missing** | Catalog / Detail | `assess_execution_capability()` | known tech but connector class is generic (`DatabaseConnector`/`SSHConnector`/`APIConnector` → `NotImplementedError`): Oracle, Windows, NGINX | A connector for this technology is not implemented yet | **Y (was)** — these showed "Ready" | ✅ FIXED — new explicit status (6 controls) |
| **Configuration Required** | Catalog / Detail | `assess_execution_capability()` | implemented connector exists, but control not wired for live execution (not in `LIVE_CONTROL_IDS` / no allow-listed target) | Connector exists; target/allow-list not configured | **Y (was)** — showed "Ready" | ✅ FIXED — new explicit status (4 controls) |
| **Dependency Missing** | Catalog / Detail | `assess_execution_capability()` + `_dependency_available()` | implemented + live, but Python driver absent (PostgreSQL → `psycopg2` not importable) | Driver must be installed before execution | **Y (was)** — would have shown "Ready" then 500 at run time | ✅ FIXED — environment-aware; falls back to graceful run error too |

### Contradiction fixed: live flag vs. status

- **OS-001** was listed in `LIVE_CONTROL_IDS` but its technology is `Unknown`. Before the fix it rendered status **Unsupported Technology** while the **Run Query button was enabled** — a direct contradiction. `is_live_execution_enabled()` now additionally requires `assess_execution_capability().executable`, so OS-001 (and any non-executable control) no longer offers Run. ✅ FIXED.
- **APPSEC-001 / APPSEC-002** appear in `LIVE_CONTROL_IDS` but **do not exist** in the loaded control library — dead references with no UI impact (no rows). ⚠️ Documented; recommend pruning the constant in a future content pass (not changed here to avoid altering the curated live set semantics).

## Query Execution status (`predefined_query_audit`)

| Status | Location | Backend Source | Actual Logic | Issue |
|---|---|---|---|---|
| **Success** | Detail → Result/Audit Trail | `record_execution_audit(...,"Success")` | Connector returned `success=True` | N — reflects real connector result |
| **Failed** | Detail → Result/Audit Trail | `record_execution_audit(...,"Failed")` | Connection or query failure (graceful, structured) | N — now also covers `connector_unavailable` (psycopg2 missing) without a 500 |

## Evidence Explorer / Evidence Workflow status

| Status | Location | Backend Source | Actual Logic | Issue |
|---|---|---|---|---|
| Pending / Submitted / Approved / Rejected | Evidence Explorer tabs, Dashboard Evidence tab | `ecs_state` evidence/workflow state; `resubmission.py` | Reflects the workflow record's actual state | N |
| **Rejected** (with context) | Dashboard → Evidence → Evidence Rejections | `ecs_state.rejected_controls[key]` = `{reason, rejected_by, rejected_at, resubmission_stage, internal}` | Real per-rejection record | **Y (was)** — table omitted timestamp & workflow state | ✅ FIXED — added Rejected At + Workflow State columns |

## Dashboard / Framework KPIs

| KPI status | Location | Backend Source | Logic | Issue |
|---|---|---|---|---|
| Audit Readiness band (Ready / At Risk / Not Ready) | Dashboards | `sufficiency_engine` band thresholds | Score-banded; deterministic | N — covered by `tests/test_sufficiency_engine_phase5_2a.py` |
| Framework "Ready" (onboarding) | AI-SDLC onboarding | onboarding engine | Distinct concept from PQ execution; unchanged | N |

## Summary of fixes applied

1. `assess_execution_capability()` is now the single source of truth for predefined-query status (Manual / Unsupported Technology / Connector Missing / Configuration Required / Dependency Missing / Ready).
2. `is_live_execution_enabled()` requires genuine executability → removes the OS-001 Run-button contradiction.
3. Catalog + Detail badges render all six statuses with an explanatory tooltip (`capability_reason`).
4. Dashboard Evidence Rejections table now shows **Rejected At** and **Workflow State**.

All KPI counts (Total 37 / Predefined 37 / Manual 0 / Frameworks 13 / Unsupported 21) are unchanged — only status truthfulness improved.
