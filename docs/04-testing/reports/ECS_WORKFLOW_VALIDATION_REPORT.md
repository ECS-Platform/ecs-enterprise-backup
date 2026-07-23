# ECS Workflow Validation Report (Phase 1)

**Mode:** READ-ONLY / ANALYSIS / REPORTING. **No workflow logic changes. No commits.** **Grounding:** `modules/shared/services/evidence_workflow_engine.py`, `modules/frameworks/engines/framework_workflow_engine.py` + `framework_onboarding_engine.py`, `modules/ai_sdlc/engines/ai_sdlc_workflow_engine.py`, `modules/operations/engines/predefined_queries_engine.py`, `ecs_platform/repository/schema.sql` (`observations`, `evidence_reviews`), `app/evidence_intel/models.py` (`EvidenceStatus`), `docs/WORKFLOWS/*`. Builds on [Workflow Orchestration Guide](../../02-architecture/architecture/ECS_WORKFLOW_ORCHESTRATION_GUIDE.md).

---

## 1. Workflow validation matrix

| Workflow | Engine / backing | States verified | Actors | Status |
|---|---|---|---|---|
| **Evidence workflow** | `evidence_workflow_engine.py`, `EvidenceStatus` enum | Draft→Collected→Submitted→UnderReview→Approved/Rejected→Resubmit | Owner, Reviewer, Auditor | ✅ Implemented |
| **Approval workflow** | `evidence_workflow_engine` + `evidence_reviews` table; `/evidence/review` | UnderReview→Approved/Rejected (+reason) | Auditor | ✅ Implemented |
| **Framework workflow** | `framework_workflow_engine.py`, `framework_onboarding_engine.py` | Onboard→Load→Activate→Review | FW Owner, Compliance, Auditor | ✅ Implemented |
| **Predefined query workflow** | `predefined_queries_engine.py` (+ `query_connectors`) | Control→Query→Detect tech→Execute→Parse→Evidence | Ops | ✅ Implemented (live exec needs connector config) |
| **Observation workflow** | `observations` table (durable) + in-memory state | Open→In Progress→Closed | Owner, Auditor | ⚠ Partial (see WF-P2-01) |
| **RAF workflow** | *No dedicated engine* | — | — | ⚠ Composite/Inferred (see WF-P2-02) |

## 2. Detailed findings

### 2.1 Evidence + Approval (✅)
`EvidenceStatus` enum (`Draft, Collected, Submitted, ...`) defines the canonical state machine; reviews persist to `evidence_reviews(status: Approved/Rejected/UnderReview/Collected/Expired)`. Approval/rejection writes are RBAC-gated (auditor) and audit-logged (`audit_log`). State-transition matrix documented in [ECS_STATE_TRANSITION_MATRIX.md](../../02-architecture/architecture/ECS_STATE_TRANSITION_MATRIX.md). **Validated, unchanged.**

### 2.2 Framework workflow (✅)
Onboarding lifecycle (`framework_onboarding_engine`) covers import/load/activate/review with RBAC predicates (`can_manage_framework_onboarding`, `can_review_framework_onboarding`). Surfaced on Framework Loader/Admin screens. **Validated.**

### 2.3 Predefined query workflow (✅ / conditional)
`predefined_queries_engine` loads the control library, deterministically detects technology (`TECH_SIGNATURES`), and routes to connectors. **Live execution requires `CONNECTOR_CONFIG` loaded** (`_connector_config_loaded()`); demo mode reports without executing. PostgreSQL queries constrained by allow-list (read-only). **Validated; live-exec is environment-dependent — see [Predefined Query Readiness](../../03-development/operations/ECS_PREDEFINED_QUERY_READINESS_REPORT.md).**

### 2.4 Observation workflow (⚠ Partial)
A durable `observations` table exists (with `status, severity, remediation_plan, closed_by/at`, additive columns), **but the schema comments state the observation workflow still uses in-memory state** ("Created but NOT yet wired into the observation workflow"). So observations render/close in-session but durable persistence is not fully wired.
- **This is a code-wiring gap → DO NOT IMPLEMENT. Document only.**

### 2.5 RAF workflow (⚠ Composite/Inferred)
No dedicated "RAF" (Risk Acceptance/Assessment Form) engine exists in code (the only `RAF` text matches are the substring of "D**RAF**T"). Risk acceptance is currently handled via the **exception/technical-debt workflow** (`/mvp/exceptions`, `/mvp/exception-governance`) plus observations. RAF as a first-class artifact is **not implemented**.

## 3. Gap classification

| ID | Finding | Severity | Recommendation (document only — DO NOT IMPLEMENT) |
|---|---|---|---|
| WF-P2-01 | Observation workflow uses in-memory state despite durable table | **P2** | Recommend wiring `insert/update_observation()` to the durable table in a future, separately-approved change. Document current behavior for UAT. |
| WF-P2-02 | No first-class RAF workflow | **P2** | Document that risk acceptance = exception/TD workflow today; propose dedicated RAF entity for Phase 2. |
| WF-P3-01 | Predefined-query live exec needs connector config | **P3** | Document environment prerequisite; no code change. |

## 4. Verdict
**Workflow layer: GO for demo/UAT with documented caveats.** Evidence, approval, framework, and predefined-query workflows are implemented and validated. Observation persistence (P2) and RAF (P2) are documented gaps requiring future, separately-approved code work — intentionally **not** implemented here.

## Cross-references
- [Workflow Orchestration Guide](../../02-architecture/architecture/ECS_WORKFLOW_ORCHESTRATION_GUIDE.md) · [State Transition Matrix](../../02-architecture/architecture/ECS_STATE_TRANSITION_MATRIX.md) · [Predefined Query Readiness](../../03-development/operations/ECS_PREDEFINED_QUERY_READINESS_REPORT.md) · [Data Architecture](../../02-architecture/architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
