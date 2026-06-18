# ECS Master Use Case Registry

**Type:** Unified, authoritative use-case index (single registry). **Mode:** Documentation only. No code/UI/DB changes. No commits.
**Purpose:** ONE registry that unifies every documented ECS use case across sources, with status/persona/module/framework/workflow/evidence/control/AI/integration/owner/priority. **Reuses existing definitions by reference — does not redefine them.**
**Sources reconciled** (see [Document Reconciliation Report](../executive/ECS_DOCUMENT_RECONCILIATION_REPORT.md)):
- [Master Use Case Catalog](ECS_MASTER_USE_CASE_CATALOG.md) (all-domain, A–N)
- [Master Use Case & LLM Reference](../AI/ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md) (AI/integration lens, SoT for AI/LLM detail)
- [AI Use Case Catalog V2](../AI/ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md)

**Status legend:** ✅ Implemented · ⚙ Implemented (enable/config) · 🟡 Partial · 🔵 Target/Inferred. **Priority:** P1/P2/P3 (per [LLM Priority Matrix](../AI/ECS_LLM_USE_CASE_PRIORITY_MATRIX.md) & [Phase1 Roadmap](../PHASE1/ECS_PHASE1_EXECUTION_ROADMAP.md)). **AI/Integ:** Y/N(+detail). Full definitions live in the source docs — this is the registry index.

---

## A. Audit (source: Master Catalog UC-A01–A12)
| ID | Name | Status | Persona | Module | Framework | Workflow | Evidence | Control | AI | Integ | Owner | Pri |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| UC-A01 | Audit readiness scoring | ✅ | Auditor/Audit Mgr/CIO | Audit Prep | all | Audit prep | mapped | coverage | Y (readiness/summary) | N | Audit | P1 |
| UC-A02 | Assemble evidence pack | ✅ | Auditor | Reports | scoped | Report gen | export | — | Opt (summary) | N | Audit | P1 |
| UC-A03 | Pre-audit gap ID | ✅ | Compliance | Completeness | all | Audit prep | coverage | gap | Y (summary) | N | Compliance | P1 |
| UC-A04 | Findings to closure | ✅ | Auditor | Risk/Exceptions | all | Exception | observation | exception | Y (drafting) | N | Audit | P2 |
| UC-A05–A12 | Freshness, posture, reuse, trail, throughput, calendar, trend, drilldown | ✅ | Auditor/CIO | various | all | various | various | various | Opt | N | Audit | P1–P2 |

## B–E. Evidence / Frameworks / Controls / Risk
| ID range | Domain | Status | Module | AI | Integ | Pri | Source |
|---|---|---|---|---|---|---|---|
| UC-E01–E15 | Evidence mgmt/reuse/version/classify/search | ✅ (E13/E14 🟡) | Evidence Repository | Y (E03/E08/E10/E13) | Opt | P1–P2 | Catalog + AI Ref |
| UC-F01–F12 | Framework assess/readiness/mapping | ✅ (F10 🔵 mapping depth) | Framework Assessment | Y (guidance/mapping) | Opt | P1–P2 | Catalog |
| UC-C01–C11 | Control library/reuse/mapping/exceptions | ✅ (C05 query-backed ⚙) | Control Library | Y (mapping/risk) | Y (C05) | P1–P2 | Catalog |
| UC-R01–R11 | Risk register/heatmaps/SLA/AI risk | ✅ | Risk Register | Y (risk assessment) | Opt | P2 | Catalog |

## F–H. Compliance / Governance / Executive
| ID range | Domain | Status | Module | AI | Integ | Pri |
|---|---|---|---|---|---|---|
| UC-K01–K11 | Compliance %, crosswalk, continuous, ISG, export | ✅ | Frameworks/Reports | Y (summary/guidance) | Opt | P1–P2 |
| UC-G01–G11 | Governance analytics, QA, lifecycle, CAB, CMDB, AI gov | ✅ | Governance | Y (recommendation) | Opt (CMDB) | P2 |
| UC-X01–X11 | CIO posture, board summary, ROI, enterprise/pan-India, heatmaps | ✅ | Executive | Y (exec summary) | N | P1–P3 |

## I–N. Operations / AI / Reporting / Search / Integrations / Workflow
| ID range | Domain | Status | Module | AI | Integ | Pri |
|---|---|---|---|---|---|---|
| UC-O01–O11 | Scheduler, connector health, query-controls, onboarding | ✅ (remote 🔵) | Scheduler/Predefined Queries | Opt (ops copilot) | **Y** | P1–P2 |
| UC-AI01–AI11 | RAG Q&A, refusal, retrieval, drafting, classify, copilots | ✅ (AI05/AI11 🔵) | AI Assistant | **Y (core)** | N | P1–P3 |
| UC-RP01–RP10 | Audit/exec/governance/risk/ROI reports | ✅ | Reports | Y (summary) | N | P1–P2 |
| UC-S01–S08 | Faceted/semantic/reuse/scoped search | ✅ | Search/AI Assistant | Y (S02) | N | P1 |
| UC-I01–I13 | Jira/Confluence/SNOW/Prisma/SP/Teams/AZDO/GitHub/Jenkins/Gitea/Figma | ⚙ (enable+validate) | Connector Framework | Opt | **Y** | P1–P2 |
| UC-W01–W10 | Onboarding, framework, evidence, approval, audit, control, exception, risk, report, AI-SDLC | ✅ (observation durable ⚙) | Workflow Engine | Opt | Opt | P1–P2 |

## Baselining & Predefined Queries (source: AI Ref §5 Cat 22–29)
| ID | Name | Status | Integration | Pri |
|---|---|---|---|---|
| UC-BL01 | Linux baselining | ✅ (demo; SSH 🔵) | Linux | P1 |
| UC-BL03 | PostgreSQL baselining | ✅ | PostgreSQL (psycopg2) | P1 |
| UC-BL09 | Trivy image scan | ✅ | Trivy | P1 |
| UC-BL10 | Gitleaks secret scan | ✅ | Gitleaks | P1 |
| UC-BL11 | SonarQube quality gate | ✅ | SonarQube | P1 |
| UC-BL02 | Windows baselining | 🔵 | Windows (WinRM) | P2 |
| UC-BL04 | Aurora MySQL baselining | 🔵 | MySQL driver | P2 |
| UC-BL05 | Yugabyte baselining | 🟡 (via PG wire — validate) | PostgreSQL-wire | P2 |
| UC-BL06 | Nginx baselining | 🟡 (via Linux) | Linux/SSH | P2 |
| UC-BL07 | Oracle baselining | 🔵 | Oracle driver | P2 |
| UC-BL08 | SQL Server baselining | 🔵 | SQL Server (pyodbc) | P2 |

## Observation / RAF (source: PHASE1 plans)
| ID | Name | Status | AI | Pri |
|---|---|---|---|---|
| UC-OB01–OB04 | Raise/track/persist/auto-close observation | ✅ (durable ⚙ flag) | Y (drafting) | P1–P2 |
| UC-RAF01 | Risk acceptance via exception | ✅ | Y (risk) | P2 |
| UC-RAF02–RAF03 | First-class RAF + ISG approval + lifecycle | 🔵 Target | Y (risk) | P2 |

## Copilots (source: AI Ref §5 Cat 37–40)
| ID | Name | Status | Persona | Mode | Pri |
|---|---|---|---|---|---|
| UC-CP01 | Audit Copilot | ✅ (RAG) | Auditor | Local | P1–P2 |
| UC-CP02 | Governance Copilot | ✅ | Governance | Local | P2 |
| UC-CP03 | Executive Copilot | ✅ | CIO/CISO | Hybrid | P2–P3 |
| UC-CP04 | Ops Governance Copilot | ✅ | Ops | Local | P2 |

---

## Registry totals
- **Catalogued use cases:** 150+ (A–N all-domain + AI/baselining/observation/RAF/copilot extensions).
- **Implemented (✅/⚙):** majority; **Target/Partial (🔵/🟡):** remote connectors, Windows/Oracle/MySQL/SQLServer baselining, first-class RAF, AI auto-classify/hybrid-fallback.
- **AI-enabled:** all AI Assistant/copilot/drafting/summary/classification/mapping use cases (local-first).
- **Integration-dependent:** operations/connector/baselining use cases.

## Cross-references
- [Master Use Case Catalog](ECS_MASTER_USE_CASE_CATALOG.md) · [Master Use Case & LLM Reference](../AI/ECS_MASTER_USE_CASE_AND_LLM_REFERENCE.md) · [LLM Implementation Matrix](../AI/ECS_LLM_IMPLEMENTATION_MATRIX.md) · [Master Integration Matrix](../INTEGRATIONS/ECS_MASTER_INTEGRATION_MATRIX.md) · [Document Reconciliation](../executive/ECS_DOCUMENT_RECONCILIATION_REPORT.md)
