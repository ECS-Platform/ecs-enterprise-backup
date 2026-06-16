# ECS Feature Reference

Part of the **ECS Product Operations Manual**. The complete catalog of features, actions, reports, exports, and the API/drilldown surface — grounded in the route registrars and engines. Use this with `ECS_SCREEN_CATALOG.md` (where features appear) and `ECS_PERSONA_GUIDE.md` (who may use them).

---

## 1. Evidence lifecycle actions (the core workflow)

Every piece of evidence moves through a state machine driven by these actions. Permission gates per `role_permissions.py` (see persona guide).

| Action | Endpoint | Who | Effect |
|---|---|---|---|
| Upload / replace evidence | `POST /evidence/upload` (`evidence_routes.py:40`) | Owner | Attach an artefact to a control; auto-map to frameworks |
| Bulk upload | `POST /mvp/upload/bulk` (`routes_mvp.py:464`) | Owner | Mass import with validation & dedup |
| Submit to auditor | `POST /submit` / `POST /evidence/submit` | Owner | Move evidence to auditor review queue |
| Review | `/evidence/review` (`app/main.py:682`) | Auditor | Open the review workspace |
| Approve | `POST /approve`, `/evidence/review/approve` | Auditor / Admin | Mark evidence approved |
| Reject | `POST /reject`, `/evidence/review/reject` | Auditor | Bounce evidence with reason |
| Reject (internal) | `POST /evidence/review/reject-internal` | Auditor | Internal rejection (not to owner) |
| Clarify | `POST /evidence/review/clarify` | Auditor | Request clarification |
| Request re-upload | `POST /evidence/review/request-reupload` | Auditor | Ask owner for a fresh artefact |
| Close observation | `POST /evidence/review/close-observation` | Auditor | Close a linked observation |
| Request resubmission | `POST /evidence/review/request-resubmission` | Auditor | Ask for resubmission |
| Upload revised | `POST /evidence/review/upload-revised` | Owner | Provide a corrected version |
| Re-evaluate | `POST /evidence/review/reevaluate` | Auditor | Re-score evidence |
| Save draft / Cancel | `POST /evidence/review/save-draft` / `/cancel` | Auditor | Persist or abandon review notes |
| Revalidate | `POST /evidence/revalidate` (`evidence_routes.py:100`) | system/owner | Re-run validation |

### Workflow management actions (`app/main.py:1261-1388`)
Cancel, Comment, Upload-version, Escalate, Clarify, Close, and **Leadership review** (`/workflow/leadership/review` → approve_closure / send_back / escalate_governance / request_rca) for executives.

### Operational remediation actions (`operational_workflows.py`)
| Action | Page | Endpoint |
|---|---|---|
| Close gap | `/mvp/workflow/close-gap` | `POST /mvp/workflow/close-gap` |
| Assign owner | `/mvp/workflow/assign-owner` | `POST /mvp/workflow/assign-owner` |
| Upload missing | `/mvp/workflow/upload-missing` | `POST /mvp/workflow/upload-missing` |
| Request re-upload | — | `POST /mvp/workflow/request-reupload` |
| Mock audit | `/mvp/workflow/mock-audit` | `POST /mvp/workflow/mock-audit/execute`, `/action` |

### Central action routers
- `POST /mvp/module/action` (`routes_mvp.py:1710`) — fans out workflow redirects, scheduler controls, report exports, Pan-India CSV, governance/evidence-approval exports.
- `POST /mvp/grc/action` (`routes_mvp.py:1698`) — generic Enterprise GRC module actions.

---

## 2. Framework features

| Feature | Endpoint | Notes |
|---|---|---|
| Browse framework dashboard | `GET /framework/{name}` | Tabs: applications/controls/evidence; ITPP drills |
| Framework KPI drill | `GET /api/framework/kpi-drill` | metric drilldown |
| Workflow / row / tab drill | `GET /api/framework/{workflow-drill,row-drill,tab-drill}` | — |
| Upload custom framework | `POST /mvp/framework-loader/upload` | Framework Loader |
| Activate framework | `POST /mvp/framework-loader/activate` | — |
| Import / onboard framework | `POST /api/framework-onboarding/import` | Framework Admin (CIO/Compliance/Admin) |
| Lifecycle transition | `POST /api/framework-onboarding/lifecycle` | — |
| Reuse decision | `POST /api/framework-onboarding/reuse-decision` | accept/reject canonical reuse |
| Export onboarding analysis | `GET /mvp/framework-admin/export/{id}?format=pdf\|excel\|csv` | — |
| Control-drill / application-scan | `GET /api/framework-loader/control-drill`, `/application-scan` | — |

**Framework catalog:** 15 frameworks, 305 controls, 702 evidence records (`framework_catalog.catalog_stats()`).

---

## 3. Operations features

| Feature | Endpoint |
|---|---|
| Run/retry/pause/resume scheduler | `POST /mvp/scheduler/{run,retry,pause,resume}` |
| Sync connector (demo) | `POST /mvp/integrations/sync`, `/mvp/integrations-hub/sync` |
| Sync connector (real, admin) | `POST /mvp/platform/sync/{connector}`, `/mvp/platform/sync-all`, `POST /api/platform/sync/{connector}` |
| Onboarding simulate / export | `POST /api/onboarding/simulate`, `/api/onboarding/export` (text) |
| Predefined query prepare / run | `POST /mvp/predefined-queries/{prepare,run}` |
| AI Ops chat / investigation / action | `POST /mvp/chat`, `/mvp/api/chat-investigation`, `/chat-action`, `/chat-response-mode` |
| Connector health | `GET /api/platform/health` |
| Browse repository evidence | `GET /api/platform/evidence`, `/evidence/repository`, `/evidence/{id}` |

**Connectors (12, `ecs_platform/connectors`):** Gitea, GitHub, SonarQube, Jenkins, Jira, Confluence, Figma, ServiceNow, Teams, SharePoint, Prisma Cloud, Azure DevOps. Operations-layer adapters: PostgreSQL, Linux, SonarQube, Gitleaks, Trivy.

---

## 4. Governance features

| Feature | Endpoint |
|---|---|
| Audit-prep drills | `GET /api/audit-prep/{kpi-drill,audit-detail,upcoming}` |
| Generate audit package | `POST /audit/package/generate` |
| Export audit bundle | `GET /audit/package/export?format=json\|text` |
| Export gap analysis | `POST /mvp/comparison/export-gaps` → `GET /mvp/exports/download/{id}` (pdf/excel/csv), preview `/mvp/exports/preview/{id}` |
| Raise exception | `POST /mvp/exceptions/raise`, `/api/exceptions/raise` |
| Module KPI drill | `GET /api/module-kpi/drill` |
| Universal / workflow drill | `GET /api/ecs/universal-drill`, `/api/ecs/workflow-drill` |
| Analytics intel | `GET /mvp/api/analytics-intel` |
| Filter options / apply | `GET /api/ecs/filters/options`, `POST /api/ecs/filters/apply` |

---

## 5. Enterprise GRC features

| Feature | Endpoint |
|---|---|
| Risk drill | `GET /api/grc-demo/risk/drill` |
| Governance drill / intel | `GET /api/grc-demo/governance/drill`, `/governance/intel` |
| Exception governance | exception state via `/mvp/exception-governance` |
| Governance QA scan / self-heal | `GET /api/ai-sdlc/governance-quality`, `/governance-scan` |

---

## 6. AI SDLC & AI Governance features

| Feature | Endpoint |
|---|---|
| Control tower tab / drill / work-item | `GET /api/ai-sdlc/control-tower/{tab/{id},drill/readiness,drill/framework,work-item/{id}}` |
| Onboarding run / drill | `GET /api/ai-sdlc/onboarding/{run,drill/framework,drill/application}` |
| Controlled document (+counts) | `GET /api/ai-sdlc/controlled-document`, `/controlled-document/counts` |
| Control / observation drill | `GET /api/ai-sdlc/{control-drill,observation-drill}` |
| Workflow review / action | `GET /api/ai-sdlc/workflow/review`, `POST /api/ai-sdlc/workflow/action` |
| SDLC drill / stage | `GET /api/ai-sdlc/sdlc/{drill,stage}` |
| Posture / registry drill | `GET /api/ai-sdlc/{posture/drill,registry/drill}` |
| Governance quality / scan | `GET /api/ai-sdlc/{governance-quality,governance-scan}` |

---

## 7. AI Assistant / RAG features

| Feature | Endpoint | Who |
|---|---|---|
| Ask the assistant | `GET /api/platform/assistant?q=…` ; pages `/mvp/ai-assistant`, `/mvp/platform/assistant` | all (read) |
| RAG status / provider | `GET /api/platform/rag/{status,gemini,llm}` | all |
| Warm RAG cache | `POST /api/platform/rag/warm` | Admin |
| Reindex RAG | `POST /api/platform/rag/reindex`, `/mvp/ai-assistant/reindex`, `/mvp/platform/assistant/reindex` | Admin |

Citation-grounded retrieval over the evidence repository via `ecs_platform/rag.py` (provider-pluggable: Ollama, Gemini, OpenAI, Azure OpenAI, Claude).

---

## 8. Reports & exports catalog

### A. Executive audit-pack catalog (30 packs)
**Engine:** `reporting_module.py` · **List:** `/mvp/reports` · **Download:** `GET /mvp/reports/download/{report_id}?format={pdf|excel|csv|xlsx}`

| # | report_id | Title | Format | Category |
|---|---|---|---|---|
| 1 | `pci-audit-pack` | PCI DSS Executive Audit Pack | PDF | Audit |
| 2 | `pci-mobile` | PCI DSS — Mobile Banking CDE Report | PDF | Audit |
| 3 | `appsec-sast` | AppSec SAST / DAST Summary | Excel | Security |
| 4 | `vapt-external` | VAPT External Pen Test Closure Report | PDF | Security |
| 5 | `dpsc-upi` | DPSC UPI Channel Compliance Pack | PDF | Regulatory |
| 6 | `csite-soc` | CSITE SOC & SIEM Governance Report | PDF | Cyber |
| 7 | `itpp-dr` | ITPP DR Readiness & Drill Summary | Excel | Operations |
| 8 | `os-baseline` | OS Baselining Hardening Export | Excel | Infrastructure |
| 9 | `db-baseline` | DB Baselining TDE Attestation Pack | PDF | Infrastructure |
| 10 | `nginx-tls` | Nginx TLS / WAF Configuration Report | PDF | Infrastructure |
| 11 | `enterprise-cio` | CIO Enterprise Governance Pack | PPT | Executive |
| 12 | `pan-india` | Pan India Regional Compliance Report | PDF | Executive |
| 13 | `rbi-cyber` | RBI Cyber Security Compliance Summary | PDF | Regulatory |
| 14 | `framework-coverage` | Cross-Framework Coverage Summary | Excel | Governance |
| 15 | `exceptions-td` | Active TD Exceptions Register | Excel | Compliance |
| 16 | `stale-evidence` | Stale Evidence Aging Report | Excel | Audit |
| 17 | `audit-readiness` | Audit Readiness Scorecard | PDF | Audit |
| 18 | `remediation-velocity` | Remediation Velocity & SLA Report | Excel | Operations |
| 19 | `integration-health` | Integration Connector Health Export | Excel | Operations |
| 20 | `reuse-mapping` | Evidence Reuse Mapping Report | Excel | Governance |
| 21 | `loan-pci` | Loan System PCI Scope Report | PDF | Audit |
| 22 | `wealth-appsec` | Wealth Portal AppSec Pack | PDF | Security |
| 23 | `treasury-itpp` | Treasury Operational Resilience Pack | PDF | Operations |
| 24 | `payments-dpsc` | Payments DPSC Self-Assessment Export | PDF | Regulatory |
| 25 | `evidence-approval-summary` | Evidence Approval Summary | PDF | Governance |
| 26 | `rejection-analysis` | Rejection Analysis Report | Excel | Audit |
| 27 | `framework-validation` | Framework Validation Report | PDF | Audit |
| 28 | `exception-governance` | Exception Governance Report | PDF | Compliance |
| 29 | `td-risk-exposure` | TD Risk Exposure Report | Excel | Compliance |
| 30 | `evidence-approval-ppt` | Evidence Approval Executive Brief | PPT | Executive |

Formats: PDF (`gap_export_engine._build_pdf`), Excel (SpreadsheetML `_spreadsheet_xml`), CSV, plain-text fallback. Definitions `reporting_module.py:16-47`; generation `:166-253`.

### B. Interactive HTML reports (5 types)
**Engine:** `ecs_reports_engine.py` · **View:** `GET /mvp/reports/view/{report_type}`

| report_type | Title |
|---|---|
| `framework-adherence` | Framework Adherence Report |
| `framework-readiness` | Framework Readiness Report |
| `application-compliance` | Application Compliance Report |
| `evidence-coverage` | Evidence Coverage Report |
| `findings-remediation` | Findings and Remediation Report |

Catalog report_ids map to these view types (`ecs_reports_engine.py:174-188`).

### C. AI SDLC reports (6)
**Engine:** `ai_sdlc_reports_engine.py` · **List/detail:** `/mvp/ai-sdlc/reports`, `/reports/{id}`

| report_id | Title |
|---|---|
| `app-compliance` | Application Compliance Report |
| `fw-compliance` | Framework Compliance Report |
| `readiness` | Readiness Report |
| `control-impl` | Control Implementation Report |
| `evidence-status` | Evidence Collection Status Report |
| `findings` | Findings & Remediation Report |

### D. Other exports
| Export | Route | Format |
|---|---|---|
| Gap analysis | `POST /mvp/comparison/export-gaps` → `/mvp/exports/download/{id}` | PDF / Excel / CSV |
| Audit package | `POST /audit/package/generate`; bundle `GET /audit/package/export` | JSON / text |
| Framework onboarding | `GET /mvp/framework-admin/export/{id}` | PDF / Excel / CSV |
| Operations onboarding | `POST /api/onboarding/export` | text |
| Mock audit report | `GET /mvp/workflow/mock-audit/report` | text |
| Pan-India regional | `POST /mvp/module/action` (export_regional) | CSV |
| Governance analytics chart | `POST /mvp/module/action` (export_chart) | CSV |
| Evidence approval summary | `POST /mvp/module/action` (export_summary) | CSV |

---

## 9. Cross-cutting features

| Feature | Where | Notes |
|---|---|---|
| **Universal drilldown** | every KPI tile / chart element | `/api/ecs/universal-drill`, `module_kpi_drill_engine.py` — click any KPI to see contributing rows |
| **Metric trace / explainability** | KPI modals | `metric_trace_service.py` — shows numerator/denominator + historical trend |
| **Governance chatbot** | most pages (chat box) | `chatbot_engine.py`; deep-links via `chatbot_nav.py` |
| **Nav badge counters** | left sidebar | `nav_counter_engine.py` — pending items per framework/module |
| **Role-scoped filtering** | all data screens | `role_filter_scope.py` (demo) / `app/auth/scope.py` (flag-gated) |
| **Standard filters** | analytics screens | `standard_filter_engine.py`, `global_filter_engine.py` |
| **Audit trail** | review & workflow | `audit_trail.py` — every action logged with actor/time |
| **Health / readiness probes** | ops | `GET /healthz`, `GET /readyz` |

---

## 10. Feature flags (selected)

ECS gates several features behind environment flags (default OFF unless noted). See `docs/ENVIRONMENT_CONFIGURATION.md` for the full table.

| Flag | Gates |
|---|---|
| `DEMO_MODE` | bypass auth/RBAC/page guards; use synthetic data |
| `ECS_AUTH_ENABLED` | JWT/OIDC authentication middleware |
| `RBAC_ENFORCEMENT_ENABLED` / `RBAC_PAGE_ENFORCEMENT_ENABLED` / `RBAC_SCOPE_FILTERING_ENABLED` / `RBAC_MUTATION_ENFORCEMENT_ENABLED` | canonical PolicyEngine enforcement |
| `ROI_CENTER_ENABLED` | ROI & Value Realization center |
| `SUFFICIENCY_ENGINE_ENABLED` | evidence sufficiency scoring |
| `OBSERVATION_READINESS_ENABLED` | observation closure readiness |
| `EVIDENCE_PORTFOLIO_ENABLED` | portfolio analytics |

See `ECS_USER_JOURNEYS.md` for how these features chain into end-to-end workflows.
