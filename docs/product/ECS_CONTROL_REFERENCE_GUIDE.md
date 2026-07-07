# ECS Control Reference Guide

**Type:** Control management reference. **No code/UI/DB changes.** **Grounding:** `modules/frameworks/engines/framework_catalog.py` (305 controls across 15 frameworks), `ecs_platform/repository/schema.sql` (`controls`, `control_catalog`, `control_framework_crosswalk`, `evidence_control_map`), governance/completeness engines, `/mvp/exceptions`, `/mvp/exception-governance`. Inferred items marked **[Inferred/Target]**.

---

## 1. Control library

305 controls organised by 15 frameworks in `FRAMEWORK_CATALOG`. Each control entry: `control` (code + title), `primary_evidence`, weighting fields. Persisted to `controls`/`control_catalog`; demo derives from the catalog. See [Frameworks library](../product/_legacy_FRAMEWORKS_index.md).

## 2. Control ownership

Controls map to a Control Owner persona (RBAC `control_owner` / framework owner). Ownership drives accountability on Completeness, Coverage, and Audit Prep screens. Application-level owners derive from `framework_catalog` owner lists (e.g., "R. Mehta (App Owner)").

## 3. Control lifecycle

`Defined → Mapped (to framework) → Evidence Assigned → Assessed/Tested → Validated (Covered) → Effective` · with `Exception/Compensating` branch and `Closure`. Reflected in Completeness (maturity), Coverage (covered), and Exceptions screens.

## 4. Control assessment, validation, testing

- **Assessment:** maturity scoring (Completeness engine) by evidence presence + sufficiency.
- **Validation:** evidence sufficiency + reviewer approval mark a control "covered" (`control_coverage()` in `governance.py`).
- **Testing:** predefined-query execution against live targets produces objective pass/fail evidence (see [Predefined Query Architecture](../OPERATIONS/ECS_PREDEFINED_QUERY_ARCHITECTURE.md)). Controls without query support are flagged "manual".

## 5. Control reuse & cross-framework controls

`control_framework_crosswalk` + `CONTROL_CROSSWALK` map one control to many frameworks (e.g., encryption/access controls shared across PCI DSS, ISO27001, RBI Cyber). One validated control + its evidence satisfies multiple regulations — the reuse engine quantifies the multiplier.

## 6. Control mapping

- **Control → Framework:** `control_framework_crosswalk`.
- **Evidence → Control:** `evidence_control_map`.
- **Control → Regulatory theme:** Regulatory Mapping screen (`/mvp/regulatory`).

## 7. Control effectiveness

Effectiveness = covered + fresh + approved evidence + (where applicable) passing query results. Surfaced as coverage/maturity %; declining freshness reduces effectiveness (Evidence Health).

## 8. Control exceptions & technical debt

`/mvp/exceptions` raises exceptions/TD; `/mvp/exception-governance` runs the lifecycle (active/approved/expiring, CAB-style approval, expiry). Exceptions reduce dynamic completeness via penalty (`missing_evidence_engine`).

## 9. Compensating controls

When a primary control cannot be met, a compensating control + justification is recorded via the exception workflow. **[Inferred/Target]** for a dedicated compensating-control register beyond the exception flow.

## 10. Control closure

Closure when evidence approved + exception resolved/expired or remediation complete. Audit trail in `audit_log`; reflected in closure-rate trend (Trends screen).

## 11. Worked examples

| Control | Framework(s) | Primary evidence | Validation | Reuse |
|---|---|---|---|---|
| Encryption at rest | PCI DSS, ISO27001, RBI Cyber | KMS/DB config export | DB query / config evidence | high (cross-fw) |
| Encryption in transit | PCI DSS, AppSec, Nginx | TLS/Nginx config | Nginx query | high |
| Patch compliance | OS/DB Baselining, RBI Cyber | OS patch report | Linux query | medium |
| Backup compliance | ITDRM, ISO27001 | backup job logs | scheduler/connector | medium |
| Vulnerability management | VAPT, AppSec | Trivy/scan report | Trivy/SonarQube query | high |
| Access management | PCI DSS, ISO27001, CSITE | IAM/access review | connector + manual | high |

---

## Cross-references
- Evidence: [ECS_EVIDENCE_REFERENCE_GUIDE.md](../evidence-management/ECS_EVIDENCE_REFERENCE_GUIDE.md)
- Frameworks: [Frameworks library](../product/_legacy_FRAMEWORKS_index.md)
- Query testing: [ECS_PREDEFINED_QUERY_ARCHITECTURE.md](../OPERATIONS/ECS_PREDEFINED_QUERY_ARCHITECTURE.md)
- Data model: [ECS_DATA_ARCHITECTURE_REFERENCE.md](../architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
