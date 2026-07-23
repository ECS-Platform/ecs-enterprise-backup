# ECS Screen Catalog & Audit (Phase 4)

**Audit date:** 2026-06-17. Every route inventoried with **Route · Page Name · Module · Persona Access · Purpose · Dependencies · Documentation (Y/N) · Screenshot (Y/N)**. "Documentation" = covered in `docs/01-product/product/PRODUCT_MANUAL_ECS_SCREEN_CATALOG.md`. "Screenshot" = file present under `docs/01-product/product/screenshots/`. Persona access reflects intended RBAC (all personas in demo mode).

**Summary:** ~79 HTML screens · 66 screenshots captured · **HTML screen documentation coverage ≈ 100%**, **screenshot coverage ≈ 84%** (forms, drilldown modals, redirects, and path-param detail pages are documented but not separately shot).

---

## Core / auth

| Route | Page Name | Module | Persona | Purpose | Dependencies | Doc | Shot |
|---|---|---|---|---|---|:--:|:--:|
| `/` | Login | executive_overview | all | Persona picker | `login.html`, `POST /login` | Y | Y (01) |
| `/access-denied` | Access Denied | app | all | RBAC 403 page | `page_guard.py` | Y | N (guard off in demo) |
| `/dashboard` | Main Dashboard | executive_overview | Owner/Auditor | Work queue | `workflow_module` | Y | Y (02,03) |
| `/dashboard/cio` | CIO Dashboard | executive_overview | CIO | Enterprise posture | `demo_metrics` | Y | Y (04) |
| `/evidence/review` | Evidence Review | governance | Auditor/Owner | Approve/reject workspace | `evidence_review` | Y | N (form) |

## Executive Overview

| Route | Page Name | Module | Persona | Purpose | Dependencies | Doc | Shot |
|---|---|---|---|---|---|:--:|:--:|
| `/dashboard/vertical-head` | Vertical Head Dashboard | executive_overview | Vertical Head | Vertical posture | `demo_metrics` | Y | Y (05) |
| `/dashboard/compliance-head` | Compliance Dashboard | executive_overview | Compliance/Security | Compliance posture | `demo_metrics` | Y | Y (06) |
| `/dashboard/functional-head` | Functional Head Dashboard | executive_overview | Functional Head | Function posture | `demo_metrics` | Y | Y (07) |
| `/mvp/roi` | ROI & Value Realization | executive_overview | CIO/Exec | ROI quantification | `roi/workbook.py` | Y | Y (08) |
| `/mvp/demo-overview` | Demo Overview | executive_overview | Demo/CIO | Demo cockpit | `ecs_mock_engine` | Y | Y (09) |
| `/mvp/enterprise` | Enterprise | executive_overview | CIO/Heads | Org KPIs | `executive_analytics_engine` | Y | Y (10) |
| `/mvp/pan-india` | Pan India | executive_overview | CIO/Vertical | Regional posture | `executive_analytics_engine` | Y | Y (11) |
| `/mvp/reports` | Reports | executive_overview | Auditor/CIO/Compliance | Export center | `reporting_module` | Y | Y (12) |
| `/mvp/reports/view/{report_type}` | Report Viewer | executive_overview | export roles | Interactive HTML report | `ecs_reports_engine` | Y | N (path-param) |
| `/mvp/trends` | Trends | executive_overview | CIO/Compliance | Historical analytics | `trends_analytics_engine` | Y | Y (13) |

## Frameworks

| Route | Page Name | Module | Persona | Purpose | Dependencies | Doc | Shot |
|---|---|---|---|---|---|:--:|:--:|
| `/framework/{name}` | Framework page (15) | frameworks | Compliance/Auditor/FW Owner/Owner | Per-framework compliance | `framework_catalog`, `framework_dashboards` | Y | Y (14, PCI DSS) |
| `/mvp/framework-loader` | Framework Loader | frameworks | Compliance/FW Owner | Upload/activate library | `framework_loader_service` | Y | Y (15) |
| `/mvp/framework-admin` | Framework Administration | frameworks | FW Owner/Compliance/CIO/Admin | Onboarding lifecycle | `framework_onboarding_engine` | Y | Y (16) |
| `/mvp/framework-admin/export/{id}` | Onboarding export | frameworks | FW Owner | PDF/Excel/CSV export | `framework_onboarding_engine` | Y | N (download) |

## Operations

| Route | Page Name | Module | Persona | Purpose | Dependencies | Doc | Shot |
|---|---|---|---|---|---|:--:|:--:|
| `/mvp/scheduler` | Scheduler | operations | Ops/Admin | Collection scheduler | `scheduler_intelligence` | Y | Y (17) |
| `/mvp/predefined-queries` | Predefined Queries | operations | Ops | Query catalog | `predefined_queries_engine` | Y | Y (18) |
| `/mvp/predefined-queries/detail` | Query Detail | operations | Ops | Query execution prep | `predefined_queries_engine` | Y | N (path-param) |
| `/mvp/integration-health` | Integration Health | operations | Admin/Ops | Connector health | `ecs_platform/ingestion` | Y | Y (19) |
| `/mvp/evidence-explorer` | Evidence Explorer | operations | Admin/Auditor | Browse repo evidence | `ecs_platform` | Y | Y (20) |
| `/mvp/ai-ops-assistant` | AI Ops Assistant | operations | Ops | Governance copilot | `ai_ops_assistant_engine` | Y | Y (21) |
| `/mvp/ai-ops-assistant/summary/{mode}` | AI Ops Summary | operations | Ops | Response-mode summary | `ai_ops_summary_engine` | Y | N (path-param) |
| `/mvp/upload` | Bulk Upload | operations | Owner | Mass import | `evidence_repository` | Y | Y (22) |
| `/mvp/integrations` | Integrations | operations | Ops | Connectors | `integrations_module` | Y | Y (23) |
| `/mvp/onboarding` | Onboarding | operations | Ops | App onboarding | `onboarding_engine` | Y | Y (24) |

## Governance

| Route | Page Name | Module | Persona | Purpose | Dependencies | Doc | Shot |
|---|---|---|---|---|---|:--:|:--:|
| `/mvp/audit-prep` | Audit Prep | governance | Auditor/Compliance | Readiness cockpit | `audit_prep_data` | Y | Y (25) |
| `/mvp/evidence-health` | Evidence Health | governance | Owner/Governance | Quality scoring | `evidence_health_engine` | Y | Y (26) |
| `/mvp/reuse` | Evidence Reuse | governance | Compliance | Reuse graph | `framework_intelligence` | Y | Y (27) |
| `/mvp/lifecycle` | Lifecycle | governance | Compliance | Evidence lifecycle | `governance_lifecycle_engine` | Y | Y (28) |
| `/mvp/completeness` | Completeness | governance | Compliance/Owner | Gap analysis | `governance_completeness_engine` | Y | Y (29) |
| `/mvp/comparison` | App Comparison | governance | Heads/Compliance | Posture comparison | `comparison_engine` | Y | Y (30) |
| `/mvp/search` | Search | governance | Auditor/Compliance | Evidence discovery | `search_module` | Y | Y (31) |
| `/mvp/evidence-approval` | Evidence Approval Analytics | governance | Auditor/Governance | Approval throughput | `evidence_approval_engine` | Y | Y (32) |
| `/mvp/workflow/close-gap` | Close Gap | governance | Owner/Auditor | Remediation form | `operational_workflows` | Y | N (form) |
| `/mvp/workflow/assign-owner` | Assign Owner | governance | Auditor/Compliance | Assignment form | `operational_workflows` | Y | N (form) |
| `/mvp/workflow/upload-missing` | Upload Missing | governance | Owner | Upload form | `operational_workflows` | Y | N (form) |
| `/mvp/workflow/mock-audit` | Mock Audit | governance | Auditor | Mock audit | `operational_workflows` | Y | N (form) |

## Evidence Governance (platform)

| Route | Page Name | Module | Persona | Purpose | Dependencies | Doc | Shot |
|---|---|---|---|---|---|:--:|:--:|
| `/mvp/platform/scorecard` | Role Scorecard | operations | all | Role scorecard | `ecs_platform/governance` | Y | Y (33) |
| `/mvp/platform/executive-summary` | Executive Summary | operations | Exec | Platform exec summary | `ecs_platform/governance` | Y | Y (34) |
| `/mvp/platform/audit-readiness` | Audit Readiness | operations | Auditor | Composite readiness | `ecs_platform/governance` | Y | Y (35) |
| `/mvp/platform/onboarding` | Application Onboarding | operations | Admin/Ops | Register app | `routes_governance` | Y | Y (36) |
| `/mvp/platform/inventory` | Application Inventory | operations | Admin | App catalog | `routes_governance` | Y | Y (37) |
| `/mvp/platform/application/{slug}` | Application Detail | operations | Admin | App detail | `routes_governance` | Y | N (path-param) |
| `/mvp/platform/control-coverage` | Control Coverage | operations | Compliance | Coverage | `ecs_platform/governance` | Y | Y (38) |
| `/mvp/platform/framework-coverage` | Framework Coverage | operations | Compliance | Coverage | `ecs_platform/governance` | Y | Y (39) |
| `/mvp/platform/evidence-reuse` | Evidence Reuse (platform) | operations | Compliance | DB reuse | `ecs_platform/governance` | Y | Y (40) |
| `/mvp/platform/evidence-lifecycle` | Evidence Lifecycle (platform) | operations | Admin | Lifecycle review | `routes_governance` | Y | Y (41) |
| `/mvp/platform/scheduler` | Collection Scheduler (platform) | operations | Admin | Connector schedules | `routes_governance` | Y | Y (42) |
| `/mvp/platform/assistant` | AI Assistant (platform) | operations | all | RAG assistant | `ecs_platform/rag` | Y | (see 43) |
| `/mvp/ai-assistant` | AI Assistant (Chat) | operations | all | RAG chat | `ecs_platform/rag` | Y | Y (43) |

## Enterprise GRC

| Route | Page Name | Module | Persona | Purpose | Dependencies | Doc | Shot |
|---|---|---|---|---|---|:--:|:--:|
| `/mvp/risk-register` | Risk Register | enterprise_grc | Governance/Risk | Risk governance | `grc_module_demo` | Y | Y (44) |
| `/mvp/exceptions` | Exceptions / TD | enterprise_grc | Compliance/Owner | TD workflow | `exception_state_engine` | Y | Y (45) |
| `/mvp/exception-governance` | Exception Governance | enterprise_grc | Compliance | TD lifecycle/CAB | `exception_state_engine` | Y | Y (46) |
| `/mvp/cmdb` | CMDB / Assets | enterprise_grc | Admin | Asset inventory | `enterprise_grc` | Y | Y (47) |
| `/mvp/regulatory` | Regulatory Mapping | enterprise_grc | Compliance | Crosswalk | `executive_analytics_engine` | Y | Y (48) |
| `/mvp/heatmaps` | Executive Heatmaps | enterprise_grc | CIO/MD | Heatmaps | `executive_analytics_engine` | Y | Y (49) |
| `/mvp/integrations-hub` | Integrations Hub | enterprise_grc | Admin | Integration orchestration | `integration_health_engine` | Y | Y (50) |
| `/mvp/correlation` | Cross-Tool Correlation | enterprise_grc | Admin | Correlation chains | `correlation_engine` | Y | Y (51) |
| `/mvp/governance-analytics` | Governance Analytics | enterprise_grc | CIO/Compliance | Governance intel | `governance_intelligence` | Y | Y (52) |

## AI SDLC Governance

| Route | Page Name | Module | Persona | Purpose | Dependencies | Doc | Shot |
|---|---|---|---|---|---|:--:|:--:|
| `/mvp/ai-sdlc` | AI SDLC Home | ai_sdlc | AI SDLC Owner | Landing | `ai_sdlc_governance_service` | Y | Y (53) |
| `/mvp/ai-sdlc/control-tower` | Control Tower | ai_sdlc | AI SDLC Owner | Readiness heatmap | `ai_sdlc_control_tower_engine` | Y | Y (54) |
| `/mvp/ai-sdlc/onboarding` | AI SDLC Onboarding | ai_sdlc | AI SDLC Owner | Onboard app | `ai_sdlc_onboarding_engine` | Y | Y (55) |
| `/mvp/ai-sdlc/requirements` | Requirements stage | ai_sdlc | AI SDLC Owner | Stage worklist | `ai_sdlc_workflow_engine` | Y | Y (56) |
| `/mvp/ai-sdlc/design` | Design stage | ai_sdlc | AI SDLC Owner | Stage worklist | `ai_sdlc_workflow_engine` | Y | Y (57) |
| `/mvp/ai-sdlc/development` | Development stage | ai_sdlc | AI SDLC Owner | Stage worklist | `ai_sdlc_workflow_engine` | Y | Y (58) |
| `/mvp/ai-sdlc/testing` | Testing stage | ai_sdlc | AI SDLC Owner | Stage worklist | `ai_sdlc_workflow_engine` | Y | Y (59) |
| `/mvp/ai-sdlc/golive` | Go-Live stage | ai_sdlc | AI SDLC Owner | Go-Live gate | `ai_sdlc_workflow_engine` | Y | Y (60) |
| `/mvp/ai-sdlc/evidence` | Evidence Collection | ai_sdlc | AI SDLC Owner | Evidence status | `ai_sdlc_evidence_governance` | Y | Y (61) |
| `/mvp/ai-sdlc/findings` | Findings & Remediation | ai_sdlc | AI SDLC Owner | Findings | `ai_sdlc_governance_mock` | Y | Y (62) |
| `/mvp/ai-sdlc/reports` | AI SDLC Reports | ai_sdlc | AI SDLC Owner | 6 reports | `ai_sdlc_reports_engine` | Y | Y (63) |
| `/mvp/ai-sdlc/reports/{id}` | AI SDLC Report detail | ai_sdlc | AI SDLC Owner | Report detail | `ai_sdlc_reports_engine` | Y | N (path-param) |
| `/mvp/ai-sdlc/evidence/view/{id}` | Evidence Viewer | ai_sdlc | AI SDLC Owner | Evidence detail | `ai_sdlc_document_artifacts` | Y | N (path-param) |
| `/mvp/ai-governance` | AI Governance Posture | ai_sdlc | AI Gov Owner | AI compliance | `ecs_ai_governance_drilldowns` | Y | Y (64) |
| `/mvp/ai-registry` | AI Model & Prompt Registry | ai_sdlc | AI Gov Owner | Registry | `ai_sdlc_knowledge_repository` | Y | Y (65) |
| `/mvp/governance-quality` | Governance Quality | ai_sdlc | Admin | Governance QA | `ecs_governance_qa_engine` | Y | Y (66) |

## Probes & utility (non-screen)

| Route | Purpose | Doc | Shot |
|---|---|:--:|:--:|
| `/healthz` | Liveness probe | Y | N |
| `/readyz` | Readiness probe | Y | N |
| `/logout` | Sign out | Y | N |
| `/evidence/repository`, `/evidence/{id}` | Evidence JSON API | Y | N |

---

## Audit findings

| Finding | Detail |
|---|---|
| **HTML screen documentation coverage** | ✅ ~100% — every screen is in `ECS_PRODUCT_MANUAL.md`/`ECS_SCREEN_CATALOG.md` |
| **Screenshot coverage** | ⚠️ 66/79 screens (~84%). Un-shot routes are forms, drilldown modals, redirects, path-param detail/download endpoints — documented but not imaged |
| **Redirect-only routes** | `/mvp/bulk-upload`→`/mvp/upload`, `/mvp/sdlc-gates`→`/mvp/ai-sdlc`, `/sdlc/{stage}`→`/mvp/ai-sdlc/{slug}` (intentional aliases) |
| **Persona access** | Intended RBAC documented in `ECS_PERSONA_GUIDE.md`; **all screens reachable by all personas in demo mode** (enforcement flag-gated off) |
| **Recommendation** | Add path-param screenshots (a framework other than PCI, a report detail, an app detail) by extending `demo-data/capture_product_manual.sh` |
