# ECS RAF (Risk Acceptance Form) Implementation Plan

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Grounding:** `/mvp/exceptions`, `/mvp/exception-governance` (routes in `modules/shared/routes/routes_mvp.py`), `app/observations/store.py` (pattern to mirror), `ecs_platform/repository/schema.sql`, `app/audit/service.py`, ISG framework (`framework_catalog._isg_catalog`). 

> **Current reality (verified):** there is **no first-class RAF entity** in ECS — the only `RAF` text matches in code are the substring of `"DRAFT"`. Risk acceptance is handled today through the **exception / technical-debt workflow** + observations. This document proposes a **design** (not an implementation) for a dedicated RAF.

---

## 1. Current handling (no dedicated RAF)

| Need | Today |
|---|---|
| Accept a risk for an unmet control | Raise an **exception/TD** via `/mvp/exceptions` |
| Govern acceptance lifecycle | `/mvp/exception-governance` (active/approved/expiring, CAB-style) |
| Track the underlying gap | **Observation** (`missing_evidence_registry` / durable `observations`) |
| Compensating control | Justification captured in the exception record |

**Gap:** no formal Risk Acceptance Form artifact with owner sign-off, risk rating, expiry, linked compensating control, and ISG approval routing as a first-class, durable, auditable entity.

## 2. Proposed RAF entity (design)

A durable `risk_acceptances` table (additive, mirrors `observations` design — idempotent, nullable columns):

| Field | Purpose |
|---|---|
| `raf_id` (unique) | identifier |
| `application_id`, `framework`, `control_id` | what risk applies to |
| `observation_id` | link to the originating gap |
| `risk_description`, `risk_rating` (Low/Med/High/Critical) | the risk |
| `compensating_control`, `justification` | mitigation rationale |
| `requested_by`, `risk_owner`, `approver` | accountability |
| `status` (Draft→Submitted→UnderReview→Approved/Rejected→Expired) | lifecycle |
| `valid_from`, `expiry_date` | time-boxed acceptance |
| `created_at/by`, `updated_at/by`, `closed_at/by`, `comments` JSONB | audit |

> Reuse the **observation store pattern**: best-effort write-through, feature-flag gated (`RAF_DURABLE_ENABLED`), `EvidenceRepository` persistence, `AuditService` `raf.*` events. No new frameworks.

## 3. RAF workflow

```
Draft ──submit──► Submitted ──reviewer pickup──► UnderReview
   ├─ approve ─► Approved (valid_from..expiry_date)
   └─ reject  ─► Rejected (back to owner)
Approved ──expiry reached──► Expired ──renew──► (new RAF)
```
Each transition: RBAC-gated + `raf.*` audit event (before/after, prev_hash chain).

## 4. ISG approval workflow (integration)

ISG (Information Security Governance) attestation should **own RAF approval** for security-impacting acceptances:
- Route security/control RAFs to the ISG approver role (today: `compliance_officer`/`security_officer`/`admin`; a dedicated `isg_approver` role is a P2 RBAC item).
- ISG sign-off recorded on the RAF (`approver`, timestamp) and reflected in ISG framework posture.
- High/Critical risk ratings require ISG + CIO co-approval (configurable).

## 5. Exception workflow (relationship)

RAF **formalizes** what the exception workflow does informally:
- An exception/TD that represents accepted risk → promote to a RAF (link `observation_id`).
- Exception governance screen surfaces RAF status (active/approved/expiring) — reuse existing UI semantics, no UI change required if RAF data maps to the exception view model.

## 6. Risk acceptance lifecycle (end-to-end)

```
Control gap (Observation) → Exception raised → RAF created (Draft)
→ risk rating + compensating control + justification → Submit
→ ISG review/approval (+CIO if High/Critical) → Approved (time-boxed)
→ monitored until expiry → renew or remediate → Closed
```

## 7. Implementation effort (if pursued — Phase 2 candidate)

| Workstream | Effort |
|---|---|
| `risk_acceptances` schema (additive) | 1 eng-day |
| `app/risk_acceptance/store.py` (mirror observation store) | 3 eng-days |
| Repository methods (upsert/get/approve/expire/list) | 2 eng-days |
| Workflow + RBAC routing (ISG approval) | 3 eng-days |
| Map to existing exception-governance view (no new UI) | 2 eng-days |
| Audit (`raf.*`) + tests | 3 eng-days |
| **Total** | **~14 eng-days** |

**Recommendation:** RAF is a **P2 enhancement** (risk acceptance works today via exceptions). Pursue only if formal, time-boxed, ISG-approved risk acceptance is a Phase-1 compliance requirement; otherwise document the exception-based path for UAT.

## Cross-references
- [Engineering Gap Analysis](ECS_P1_ENGINEERING_GAP_ANALYSIS.md) · [Observation Workflow Plan](ECS_OBSERVATION_WORKFLOW_IMPLEMENTATION_PLAN.md) · [Control Reference](../product/ECS_CONTROL_REFERENCE_GUIDE.md) · [ISG Framework](../product/ISG_ASSESSMENT.md)
