# ECS Persona Coverage Audit (Phase 1)

**Mode:** READ-ONLY / ANALYSIS / REPORTING. **No code/RBAC changes. No commits.** **Grounding:** `config/rbac.yaml` (legacy `rbac.roles` = 9 roles; canonical `rbac_catalog.roles`; `rbac_catalog.pages` = 7 dashboards; `rbac_legacy_compat.aliases`), `nav_audit/persona_shots/*`, `nav_audit/persona_validation_report.md`, `nav_audit/persona_drill_matrix.md`. Complements [Persona Guide](../product/ECS_PERSONA_GUIDE.md).

---

## 1. Implemented RBAC roles (verified)

**Legacy `rbac.roles` (9):** `admin`, `cio`, `vertical_head`, `functional_head`, `compliance_officer`, `security_officer`, `control_owner`, `auditor`, `application_owner`.
**Canonical `rbac_catalog.roles`:** adds `system_admin`; same functional set with `verb.resource` permissions + page bindings.
**Dashboard pages (`rbac_catalog.pages`, 7):** `dashboard.cio`, `.auditor`, `.compliance`, `.security`, `.owner`, `.vertical`, `.functional`.
**Legacy aliases (`rbac_legacy_compat.aliases`):** `framework_owner→compliance_head`, `ai_governance_owner→cio`, `ai_sdlc_owner→owner`, `operations_owner→owner`, `compliance_officer/security_officer→compliance_head`.

`nav_audit/persona_shots/` contains rendered evidence for cio, auditor, owner, compliance_officer, compliance_head, framework_owner, security_officer, functional_head, ai_governance_owner, ai_sdlc_owner, operations_owner.

## 2. Requested persona → role mapping

| Requested persona | Maps to RBAC role | Dedicated dashboard | Coverage |
|---|---|---|---|
| **CIO** | `cio` | `dashboard.cio` | ✅ Full |
| **CISO** | `security_officer` | `dashboard.security` | ✅ Full (CISO = security officer) |
| **Auditor** | `auditor` | `dashboard.auditor` | ✅ Full |
| **Audit Manager** | `auditor` (no distinct role) | shares auditor | ⚠ Partial — no dedicated Audit Manager role |
| **Application Owner** | `application_owner` | `dashboard.owner` | ✅ Full |
| **Function Head** | `functional_head` | `dashboard.functional` | ✅ Full |
| **Vertical Head** | `vertical_head` | `dashboard.vertical` | ✅ Full |
| **Governance** | `compliance_officer`/`admin` + Governance module | via compliance dashboard | ⚠ Partial — no distinct `governance` role |
| **Risk** | `security_officer` + Risk Register module | via security dashboard | ⚠ Partial — no distinct `risk` role |
| **Compliance** | `compliance_officer` | `dashboard.compliance` | ✅ Full |

## 3. Scope & permission validation
Each role carries a **scope** (`enterprise/vertical/function/application/control`) and scope filters (`user_assignments`/`auditor_assignments`) applied to evidence rows/vectors **before** any read (incl. AI). Permissions verified in both legacy `can:` lists and canonical `verb.resource` catalog. `nav_audit/persona_validation_report.md` confirms cross-role rendering + scoping.

## 4. Gap classification

| ID | Finding | Severity | Recommendation (document only — DO NOT IMPLEMENT) |
|---|---|---|---|
| PC-P2-01 | No dedicated **Audit Manager** role | **P2** | Document that audit management uses the `auditor` (enterprise scope) role; add a distinct role + page in a future RBAC phase if separation needed. |
| PC-P2-02 | No distinct **Governance** / **Risk** roles | **P2** | Document current mapping (Governance→compliance/admin + Governance module; Risk→security_officer + Risk Register). Consider dedicated roles in RBAC Rationalization phase. |
| PC-P3-01 | Two RBAC models coexist (legacy `rbac.roles` + canonical `rbac_catalog`, not yet enforced) | **P3** | Already documented as intentional (canonical not yet wired); reference [ECS_RBAC_LEGACY_FLAWS.md]. No change here. |
| PC-P3-02 | AI SDLC/Governance owners are aliases, not first-class roles | **P3** | Document alias mapping; promote in future if needed. |

## 5. Verdict
**Persona coverage: GO.** 7 of 10 requested personas have dedicated RBAC roles + dashboards; Audit Manager, Governance, and Risk are **Partial** (covered by mapping to existing roles + modules, no dedicated role). All mappings documented; no RBAC code modified.

## Cross-references
- [Persona Guide](../product/ECS_PERSONA_GUIDE.md) · [Role Action Matrix](../architecture/ECS_ROLE_ACTION_MATRIX.md) · [Security Reference](../production/ECS_SECURITY_REFERENCE.md) · `nav_audit/persona_validation_report.md`
