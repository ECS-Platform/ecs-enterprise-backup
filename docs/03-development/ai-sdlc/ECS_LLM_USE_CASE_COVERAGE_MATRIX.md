# ECS LLM Use Case Coverage Matrix

**Type:** Coverage documentation. **No code changed.** **Grounding:** `ecs_platform/rag.py`, `provider.py`, AI SDLC + operations engines, governance engines. **80 use cases** across all ECS domains.

**Columns:** Use Case · Persona · Local LLM (Y/N) · Cloud LLM (Y/N) · Hybrid (Y/N) · Recommended Mode · Complexity · Expected ROI.

**Notes:** *Local=Y* everywhere because the shipped provider abstraction runs all of these on local Ollama (`provider.generate/embed`). *Cloud=Y* because the same call works on any configured provider. *Hybrid=Y* because provider is config-selected per environment. **Recommended Mode = Local** for any use case touching evidence/PII (banking data residency); **Cloud/Hybrid** acceptable for non-sensitive narrative/UX tasks. ROI is a **qualitative banking estimate**, not measured.

---

## A. Audit (8)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Audit Copilot (Q&A over evidence) | Auditor | Y | Y | Y | Local | Med | High |
| Audit readiness narrative | Audit Lead | Y | Y | Y | Local | Med | High |
| Observation clustering & triage | Auditor | Y | Y | Y | Local | Med | High |
| Mock-audit findings draft | Auditor | Y | Y | Y | Local | Med | Med-High |
| Audit pack executive summary | Auditor/CIO | Y | Y | Y | Hybrid | Low | Med |
| Rejection-reason drafting | Auditor | Y | Y | Y | Local | Low | Med |
| Evidence sufficiency narrative | Auditor | Y | Y | Y | Local | Med | Med-High |
| Auditor question pre-answering | Auditor | Y | Y | Y | Local | Med | High |

## B. Evidence (9)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Evidence classification / auto-tag | App Owner | Y | Y | Y | Local | Med | High |
| Evidence summarization | Auditor | Y | Y | Y | Local | Low | High |
| Evidence quality review | Auditor | Y | Y | Y | Local | Med | High |
| Evidence deduplication (embeddings) | App Owner | Y | N* | Y | Local | Med | Med |
| Similar-evidence discovery (reuse) | App Owner | Y | N* | Y | Local | Med | High |
| Evidence recommendation (what to collect) | App Owner | Y | Y | Y | Local | Med | High |
| Evidence freshness/decay narrative | Owner/Governance | Y | Y | Y | Local | Low | Med |
| Evidence lineage explanation | Auditor | Y | Y | Y | Local | Med | Med |
| Bulk-upload auto-mapping assist | App Owner | Y | Y | Y | Local | Med | High |

\* Claude cloud provider has no embeddings (`provider.py:153`); embedding-based UCs need an embedding-capable provider (local nomic, or Gemini/OpenAI embeddings).

## C. Framework (8)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Control → framework mapping | Compliance | Y | Y | Y | Local | Med | High |
| Cross-framework correlation (reuse) | Compliance | Y | Y | Y | Local | High | High |
| Framework onboarding gap narrative | Framework Owner | Y | Y | Y | Local | Med | High |
| Control gap detection | Compliance | Y | Y | Y | Local | Med | High |
| Regulatory crosswalk explanation | Compliance | Y | Y | Y | Local | Med | Med-High |
| Control description normalization | Framework Owner | Y | Y | Y | Hybrid | Low | Med |
| New-regulation impact summary | Compliance | Y | Y | Y | Local | High | Med-High |
| Framework coverage commentary | Compliance | Y | Y | Y | Hybrid | Low | Med |

## D. Governance (8)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Governance Copilot | Governance Lead | Y | Y | Y | Local | Med | High |
| Completeness gap narrative | Compliance | Y | Y | Y | Local | Med | High |
| Policy summarization | Governance | Y | Y | Y | Local | Med | Med |
| SOP summarization | Operations | Y | Y | Y | Hybrid | Low | Med |
| Governance data-quality explanation | Admin | Y | Y | Y | Local | Low | Med |
| Exception (TD) risk analysis | Compliance | Y | Y | Y | Local | Med | Med |
| Lifecycle-stage explanation | Compliance | Y | Y | Y | Local | Low | Med |
| Attestation-readiness narrative | Governance | Y | Y | Y | Local | Med | Med-High |

## E. Risk (7)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Risk summarization for leadership | Risk/Security | Y | Y | Y | Local | Med | Med-High |
| Risk register prioritization narrative | Governance/Risk | Y | Y | Y | Local | Med | Med-High |
| VAPT findings summary | Security | Y | Y | Y | Local | Med | Med-High |
| Risk trajectory commentary | Risk | Y | Y | Y | Hybrid | Med | Med |
| Compensating-control suggestion | Compliance/Risk | Y | Y | Y | Local | Med | Med |
| Heatmap hotspot explanation | CIO/Risk | Y | Y | Y | Hybrid | Low | Med |
| Correlation chain narrative (incident→control) | Admin/Risk | Y | Y | Y | Local | High | Med-High |

## F. Executive (7)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Executive dashboard narrative | CIO/Exec | Y | Y | Y | Hybrid | Low | Med |
| Board-pack commentary | CIO | Y | Y | Y | Hybrid | Med | Med |
| ROI storyboard narrative | CIO | Y | Y | Y | Hybrid | Low | Med |
| Pan-India regional summary | Vertical Head | Y | Y | Y | Hybrid | Low | Med |
| Enterprise posture brief | CIO | Y | Y | Y | Local | Med | Med |
| Trend interpretation commentary | CIO/Compliance | Y | Y | Y | Hybrid | Low | Med |
| Stakeholder Q&A prep | CIO | Y | Y | Y | Local | Med | Med-High |

## G. Operations (8)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Operations Copilot | Ops Owner | Y | Y | Y | Local | Med | Med-High |
| Integration troubleshooting assistant | Ops Owner | Y | Y | Y | Local | Med | Med |
| Connector failure analysis | Ops Owner | Y | Y | Y | Local | Med | Med |
| Scheduler run explanation | Ops Owner | Y | Y | Y | Local | Low | Med |
| RCA generation | Operations | Y | Y | Y | Local | Med | Med-High |
| Collection-coverage narrative | Ops Owner | Y | Y | Y | Hybrid | Low | Med |
| AI-Ops investigation summary | Ops Owner | Y | Y | Y | Local | Med | Med |
| Onboarding gap narrative | Ops/App Owner | Y | Y | Y | Local | Med | Med |

## H. AI SDLC (8)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Stage-gate readiness narrative | AI SDLC Owner | Y | Y | Y | Local | Med | High |
| Requirements artifact drafting | AI SDLC Owner | Y | Y | Y | Local | Med | Med-High |
| Design/threat-model summary | AI SDLC Owner | Y | Y | Y | Local | High | Med-High |
| Test-evidence summary | AI SDLC Owner | Y | Y | Y | Local | Med | Med |
| Findings remediation suggestion | AI SDLC Owner | Y | Y | Y | Local | Med | Med-High |
| Go-live gate explanation | AI SDLC Owner | Y | Y | Y | Local | Med | High |
| Controlled-document generation | AI SDLC Owner | Y | Y | Y | Local | Med | Med |
| AI governance posture narrative | AI Gov Owner | Y | Y | Y | Local | Med | High |

## I. Knowledge Management (7)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Knowledge-base assistant (RAG) | All | Y | Y | Y | Local | Med | High |
| Document Q&A with citations | All | Y | Y | Y | Local | Med | High |
| Onboarding knowledge assistant | New joiner | Y | Y | Y | Local | Med | High |
| Glossary / KPI explainer | All | Y | Y | Y | Hybrid | Low | Med |
| Runbook assistant | Operator | Y | Y | Y | Local | Med | Med |
| Best-practice recommendation | Compliance | Y | Y | Y | Hybrid | Med | Med |
| AI registry knowledge lookup | AI Gov Owner | Y | Y | Y | Local | Low | Med |

## J. Search (6)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Natural-language evidence search | All | Y | N* | Y | Local | Med | High |
| Semantic similarity search | All | Y | N* | Y | Local | Med | High |
| Faceted retrieval (app/fw/status) | Auditor | Y | Y | Y | Local | Med | High |
| Cross-system evidence lookup | Admin | Y | Y | Y | Local | Med | Med-High |
| Control-to-evidence search | Compliance | Y | Y | Y | Local | Med | Med-High |
| Citation-grounded answer search | Auditor | Y | Y | Y | Local | Med | High |

## K. Reporting (6)

| Use Case | Persona | Local | Cloud | Hybrid | Recommended | Complexity | ROI |
|---|---|:--:|:--:|:--:|---|---|---|
| Audit-pack narrative generation | Auditor | Y | Y | Y | Local | Med | Med-High |
| Report executive summary | CIO/Compliance | Y | Y | Y | Hybrid | Low | Med |
| AI SDLC report commentary | AI SDLC Owner | Y | Y | Y | Local | Med | Med |
| Comparison/gap report narrative | Heads | Y | Y | Y | Local | Med | Med |
| Regulator-ready report phrasing | Compliance | Y | Y | Y | Local | Med | Med-High |
| Scheduled report digest | CIO | Y | Y | Y | Hybrid | Low | Med |

---

## Summary

| Domain | UCs | Local-capable | Recommended Local |
|---|:--:|:--:|:--:|
| Audit | 8 | 8 | 7 |
| Evidence | 9 | 9 | 9 |
| Framework | 8 | 8 | 6 |
| Governance | 8 | 8 | 7 |
| Risk | 7 | 7 | 5 |
| Executive | 7 | 7 | 2 |
| Operations | 8 | 8 | 7 |
| AI SDLC | 8 | 8 | 8 |
| Knowledge Mgmt | 7 | 7 | 5 |
| Search | 6 | 6 | 6 |
| Reporting | 6 | 6 | 5 |
| **Total** | **82** | **82 (100%)** | **67** |

**All 82 use cases run on local LLM** via the existing provider abstraction; cloud/hybrid are config options. Embedding-dependent UCs require an embedding-capable provider (local default works). See [Use Case Catalog V2](ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md) for full cards.
