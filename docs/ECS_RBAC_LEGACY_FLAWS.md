# ECS RBAC — Legacy Authorization Flaws Register

**Status:** Documented during Phase 2 Step 2A (RBAC compatibility shims).
**Action:** **NOT fixed in Step 2A.** Every item below is preserved bug-for-bug by
the legacy compatibility layer (`config/rbac.yaml → rbac_legacy_compat`) so that
delegation is a behavior-neutral swap. All corrections are reserved for the
future **RBAC Rationalization phase** (after compatibility migration completes).

These flaws were surfaced empirically by the differential parity test
(`tests/test_rbac_delegation_parity.py`), which compares the legacy predicate
results against the delegated results across every role × capability.

---

## A. Accidental / inconsistent grants

| # | Flaw | Evidence | Risk | Future correction |
|---|------|----------|------|-------------------|
| A1 | **`admin` / `system_admin` is NOT a superuser for several capabilities.** Legacy `can_escalate`, `can_request_reupload`, and `can_raise_exception` accept `enterprise_admin` but **not** bare `admin`. So a "System Administrator" mapped to `admin` cannot escalate or raise exceptions. | `role_permissions.py`: these sets list `enterprise_admin` only, never `admin` | Medium (admin under-privileged; surprising) | Canonical `system_admin` already gets `*`; rationalization unifies `admin`/`enterprise_admin`/`system_admin` |
| A2 | **Two different admin tokens (`admin` vs `enterprise_admin`) grant different powers.** `can_manage_framework_onboarding` accepts both; `can_review_evidence` accepts only `enterprise_admin`. | `role_permissions.AUDITOR_GOVERNANCE_ROLES = {auditor, enterprise_admin}` vs framework sets including `admin` | Medium | Single canonical `system_admin` |
| A3 | **`can_request_reupload` is auditor-only — even `enterprise_admin` cannot.** | `can_request_reupload → is_auditor` (only `auditor`) | Low | Grant via permission, not identity |

## B. Role-mapping inconsistencies

| # | Flaw | Evidence | Risk | Future correction |
|---|------|----------|------|-------------------|
| B1 | **`security_officer` is flattened to `compliance_head`.** Legacy `normalize_role` maps `security_officer → compliance_head`, so a Security Officer silently inherits ALL compliance powers (export, framework review, exception raise) and loses any security-specific identity. | `role_permissions.normalize_role` aliases | **High** (SoD: security ≠ compliance) | Canonical model already makes `security_officer` first-class |
| B2 | **`framework_owner` also flattened to `compliance_head`.** A dedicated framework owner gets full compliance authority. | same alias map | Medium | First-class `framework`-scoped role |
| B3 | **`ai_governance_owner → cio`.** An AI governance persona inherits full CIO authority (incl. exception approval). | same alias map | Medium | Dedicated AI-governance role |
| B4 | **`owner` vs `application_owner` divergence.** Legacy keeps `owner` (does not map to `application_owner`); the canonical model uses `application_owner`. Capability sets are written for `owner`. Mixed usage across engines invites mismatches. | legacy sets use `owner`; `rbac.yaml` legacy block uses `application_owner` | Medium | Single canonical key with alias |
| B5 | **Empty/unknown role defaults to `owner` (upload-capable-adjacent).** `normalize_role("")` → `owner`. A missing role is treated as an Application Owner rather than denied. | `normalize_role: (role or "owner")` | **High** (fail-toward-privilege on missing identity) | Default-deny once auth identity is mandatory |

## C. Fail-open behavior

| # | Flaw | Evidence | Risk | Future correction |
|---|------|----------|------|-------------------|
| C1 | **`action_allowed()` fails OPEN.** Any action not explicitly an upload action, for a non-auditor/non-executive role, returns `True` by default. | `role_permissions.action_allowed` final `return True` | **High** | Fail-closed enumerated catalog (deferred; preserved in 2A per instruction) |
| C2 | **RAG RBAC fails open on error.** `_rbac_filter` returns `allowed: True` on any exception. | `ecs_platform/rag.py` exception branch | Medium | Fail-closed with audited error |

## D. Coverage / consistency gaps (non-grant)

| # | Flaw | Evidence | Risk | Future correction |
|---|------|----------|------|-------------------|
| D1 | **5+ parallel authorization engines** with overlapping, divergent logic (A/B/C/D/E). | inventory in Step 2 assessment | Medium | Single PolicyEngine (canonical catalog) |
| D2 | **No `compliance_officer` preset** in platform scorecard despite being a first-class persona. | `ecs_platform/governance.py` `_ROLE_PRESETS` | Low | Add preset |
| D3 | **Predefined Query APIs have no authorization at all.** | `predefined_queries_engine.py` (no role checks) | Medium | Add `require_permission` in enforcement phase |

---

## Security improvement opportunities (for RBAC Rationalization phase)

1. **Default-deny** for missing/unknown identity (fix B5, C1, C2).
2. **First-class `security_officer`** with `security.read` only — remove compliance flattening (fix B1) to restore segregation of duties.
3. **Unify admin tokens** into one `system_admin` with explicit grants (fix A1–A3).
4. **Collapse 5 engines** into the canonical PolicyEngine (fix D1).
5. **Add authorization to Predefined Query + Platform/RAG admin APIs** (fix D3) — the API-enforcement step.
6. **Enforce page-level guards** to close direct-URL bypass (separate enforcement step).
7. **Enable scope filtering** so non-enterprise roles only see assigned data (separate step).

> None of the above are implemented in Step 2A. Step 2A only makes the existing
> behavior delegatable while remaining byte-for-byte identical.
