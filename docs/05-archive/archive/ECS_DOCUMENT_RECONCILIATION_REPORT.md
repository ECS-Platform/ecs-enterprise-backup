# ECS Document Reconciliation Report

**Type:** Documentation reconciliation + Single-Source-of-Truth (SoT) matrix. **Mode:** Documentation only. No code/UI/DB changes. **No deletions. No overwrites.** No commits.
**Phase 0 scan:** 181 markdown files under `docs/` (plus root-level `docs/*.md`). This report reconciles overlapping documents and designates one SoT per knowledge class. "Supersede" / "Archive" are **logical** designations only — **no file is deleted or modified**.

> **Action legend:** **Reuse** = authoritative, keep as-is · **Extend** = add missing analysis over time · **Merge** = fold unique content into the SoT by reference · **Supersede (logical)** = SoT exists; treat this as historical, keep for provenance · **Archive (logical)** = point-in-time report, retain for audit trail.

---

## 1. Single Source of Truth (SoT) matrix

| Knowledge class | **SoT document** | Subordinate / related (action) |
|---|---|---|
| **Use cases (all-domain)** | `docs/01-product/product/ECS_MASTER_USE_CASE_CATALOG.md` | `docs/01-product/product/ECS_MASTER_USE_CASE_REGISTRY.md` (new — unifying index, Extend) |
| **Use cases + AI/LLM/integration** | `docs/03-development/ai-sdlc/ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md` | AI catalogs below (Reference, don't duplicate) |
| **AI use-case catalogs** | `docs/03-development/ai-sdlc/ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md` | `ECS_LOCAL_LLM_USE_CASE_CATALOG.md` (Supersede-logical), `ECS_LOCAL_LLM_BANKING_USE_CASES.md` (Merge by ref), `ECS_LLM_USE_CASE_COVERAGE_MATRIX.md` (Reuse) |
| **KPI dictionary** | `docs/01-product/product/ECS_MASTER_KPI_DICTIONARY.md` | `docs/05-archive/archive/AUDIT_ECS_KPI_DICTIONARY.md`, `docs/01-product/product/PRODUCT_MANUAL_ECS_KPI_DICTIONARY.md`, `docs/01-product/product/ECS_KPI_REFERENCE.md` (all Supersede-logical → reference master) |
| **Product manual** | `docs/01-product/product/ECS_MASTER_PRODUCT_MANUAL.md` | `docs/01-product/product/PRODUCT_MANUAL_ECS_PRODUCT_MANUAL.md`, `docs/01-product/product/TRAINING_ECS_PRODUCT_MANUAL.md` (Supersede-logical) |
| **Screen catalog** | `docs/01-product/product/ECS_MASTER_PRODUCT_MANUAL.md` (screens) | `docs/01-product/product/PRODUCT_MANUAL_ECS_SCREEN_CATALOG.md`, `docs/05-archive/archive/AUDIT_ECS_SCREEN_CATALOG.md` (Reuse — audit context) |
| **Workflows** | `docs/WORKFLOWS/` set (orchestration, state, role-action, SLA, notifications, BPM, sequence) | `docs/05-archive/archive/ECS_WORKFLOW_COMPLETENESS_REPORT.md` (Archive-logical) |
| **Frameworks** | `docs/FRAMEWORKS/` (15 + `ECS_FRAMEWORK_REFERENCE.md`) | `docs/01-product/product/ECS_FRAMEWORK_COVERAGE_AUDIT.md` (Archive-logical) |
| **Evidence** | `docs/03-development/evidence-management/ECS_EVIDENCE_REFERENCE_GUIDE.md` | `docs/03-development/evidence-management/ECS_CONTROL_AND_EVIDENCE_REUSE_GUIDE.md` (Reuse) |
| **Controls** | `docs/01-product/product/ECS_CONTROL_REFERENCE_GUIDE.md` | reuse guide (Reuse) |
| **Integrations** | `docs/INTEGRATIONS/` (per-connector) + new `ECS_MASTER_INTEGRATION_MATRIX.md` | `docs/03-development/ai-sdlc/ECS_AI_CONNECTOR_COVERAGE_MATRIX.md` (Reuse) |
| **Architecture** | `docs/02-architecture/architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md` | `docs/03-development/operations/ECS_PREDEFINED_QUERY_ARCHITECTURE.md` (Reuse) |
| **AI architecture** | `docs/03-development/ai-sdlc/ECS_AI_ARCHITECTURE_REFERENCE.md` | `docs/03-development/ai-sdlc/ECS_BANKING_AI_ARCHITECTURE.md`, `ECS_MODEL_ABSTRACTION_ARCHITECTURE.md` (Reuse) |
| **Security** | `docs/03-development/production/ECS_SECURITY_REFERENCE.md` + `docs/03-development/ai-sdlc/ECS_AI_SECURITY_ARCHITECTURE.md` | — |
| **Deployment / Ops** | `docs/03-development/production/ECS_DEPLOYMENT_REFERENCE.md` + `docs/03-development/operations/` runbooks | — |
| **Production readiness** | `docs/03-development/production/ECS_PRODUCTION_READINESS_MASTER_PLAN.md` | `docs/PHASE1/*` plans (Reuse) |
| **Knowledge audits** | `docs/05-archive/archive/ECS_MASTER_KNOWLEDGE_CONSOLIDATION_REPORT.md` (new) | `ECS_FINAL_ENTERPRISE_KNOWLEDGE_AUDIT.md`, `ECS_FINAL_KNOWLEDGE_COMPLETENESS_REPORT.md` (Archive-logical) |

## 2. Document classes discovered (by directory)

| Directory | Count (approx) | Primary classes |
|---|---|---|
| `docs/AI` | 32 | AI architecture, LLM use cases, coverage matrices, validation, ops/testing/deployment guides |
| `docs/PRODUCT` | 5 | master product manual, master KPI dictionary, master use-case catalog, feature completeness |
| `docs/WORKFLOWS` | 8 | orchestration, state-transition, role-action, SLA, notification, BPM, sequence diagrams |
| `docs/FRAMEWORKS` | 18 | 15 framework refs + reference + coverage audit |
| `docs/INTEGRATIONS` | 10 | per-connector guides + README |
| `docs/03-development/operations` | ~22 | runbooks, checklists, DR, scheduler, predefined-query, onboarding |
| `docs/PHASE1` | ~10 | gap analysis + implementation plans + checklists |
| `docs/PRODUCTION` | 6 | readiness master + SSO/encryption/durability/remote/roadmap |
| `docs/executive` | ~8 | go-live, knowledge audits, workflow completeness, this report |
| `docs/UAT` `docs/AUDIT` `docs/TRAINING` `docs/EVIDENCE` `docs/CONTROLS` `docs/ARCHITECTURE` `docs/SECURITY` `docs/DEPLOYMENT` `docs/TESTING` `docs/product_manual` | remainder | validation reports, training manuals, reference guides |

## 3. Duplicate / overlap findings

| Overlap cluster | Documents | Resolution |
|---|---|---|
| **KPI dictionaries ×4** | PRODUCT master, AUDIT, product_manual, TRAINING reference | SoT = PRODUCT master; others reference it (no delete) |
| **Product manuals ×3** | PRODUCT master, product_manual, TRAINING | SoT = PRODUCT master |
| **AI use-case catalogs ×4** | V2, V1, banking-use-cases, coverage-matrix | SoT = V2; V1 superseded-logical; banking merged by reference |
| **Use-case master ×2** | PRODUCT catalog (all-domain), AI master reference (AI/integration lens) | Both retained — different lenses; unified by new Registry (Phase 2) |
| **Screen catalogs ×2** | product_manual, AUDIT | Both retained — product vs audit context |
| **Knowledge audits ×3** | enterprise knowledge audit, final completeness, this consolidation | New consolidation report is current; prior two archived-logical |

**No duplicate-content deletion performed.** All overlaps resolved by SoT designation + cross-reference.

## 4. Per-document reconciliation (key documents)
*Format: Document · Purpose · Coverage · Owner(role) · Action.*

- `PRODUCT/ECS_MASTER_USE_CASE_CATALOG.md` · all-domain use cases (A–N) · 150+ · Product · **Reuse** (SoT all-domain).
- `AI/ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md` · use cases + integration + LLM · 150+ · AI Arch · **Reuse** (SoT AI lens).
- `AI/ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md` · AI use cases · 100+ · AI Arch · **Reuse** (SoT AI catalog).
- `AI/ECS_LOCAL_LLM_USE_CASE_CATALOG.md` · earlier AI catalog · — · AI Arch · **Supersede (logical)**.
- `AI/ECS_LLM_USE_CASE_COVERAGE_MATRIX.md` · coverage matrix · — · AI Arch · **Reuse**.
- `PRODUCT/ECS_MASTER_KPI_DICTIONARY.md` · all KPIs · full · Product · **Reuse** (SoT KPIs).
- `AUDIT/ECS_KPI_DICTIONARY.md`, `product_manual/ECS_KPI_DICTIONARY.md`, `TRAINING/ECS_KPI_REFERENCE.md` · KPI subsets · partial · Product · **Supersede (logical)** → reference master.
- `WORKFLOWS/*` · workflow models/matrices · full · Workflow Arch · **Reuse**.
- `FRAMEWORKS/*` · 15 frameworks · full · Compliance Arch · **Reuse**; coverage audit **Archive (logical)**.
- `INTEGRATIONS/*` · per-connector · full · Integration Arch · **Reuse**; new master matrix **Extend**.
- `EVIDENCE/`, `CONTROLS/`, `architecture/`, `SECURITY/`, `DEPLOYMENT/` references · full · respective Arch · **Reuse**.
- `executive/ECS_FINAL_ENTERPRISE_KNOWLEDGE_AUDIT.md`, `ECS_FINAL_KNOWLEDGE_COMPLETENESS_REPORT.md` · prior audits · point-in-time · Exec · **Archive (logical)**.

## Cross-references
- [Master Use Case Registry](../../01-product/product/ECS_MASTER_USE_CASE_REGISTRY.md) · [Master Use Case & LLM Reference](../../03-development/ai-sdlc/ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md) · [Master Knowledge Consolidation Report](ECS_MASTER_KNOWLEDGE_CONSOLIDATION_REPORT.md) · [docs index](../README.md)
