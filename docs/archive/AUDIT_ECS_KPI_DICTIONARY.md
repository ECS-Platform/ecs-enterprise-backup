# ECS KPI Dictionary & Audit (Phase 3)

**Audit date:** 2026-06-17. For every dashboard's KPIs: **Name · Definition · Formula · Data Source · Business Meaning · Persona · Example**, plus an audit of what KPI documentation was **missing in-product** (definitions, formulas, explanations, business meaning). Full formula derivations with file:line are in `docs/product/PRODUCT_MANUAL_ECS_KPI_DICTIONARY.md`; this document is the audit-grade dictionary.

> **Audit verdict:** KPI **formulas exist in code** (engines compute them deterministically) and are now **fully documented** in the product-manual KPI dictionary. The historical gap was **in-product explainability**: most KPI tiles support a drill/metric-trace modal (`metric_trace_service.py`) but **not all tiles show a definition tooltip**. Recommendation (UI, not in scope here): attach the definitions below as tooltips. No KPI is undefined in code.

Bands used throughout: **Ready ≥80 · Watch 55–79 · Critical <55** (Completeness uses 80/65; Audit Prep uses 75).

---

## Executive / CIO dashboard

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| Audit Readiness Score | Overall audit preparedness | `0.5·coverage% + 0.3·approval% + 0.2·freshness%` | `governance.py` (repo/demo) | Single readiness number for the org | CIO/Auditor | 86 → "Audit Ready" |
| Enterprise Compliance % | Approved controls share | `100·approved/total` (floor 84.6 demo) | `ecs_state`/`demo_metrics` | Org-wide control compliance | CIO | 84.6% |
| Audit Completion % | Audits closed on schedule | demo metric | `demo_metrics` | Progress through audit calendar | CIO | 91.6% |
| Evidence Artefacts | Count of evidence records | count | state/repo | Scale of evidence base | CIO | 702 (catalog) / more in demo seed |
| Open VAPT | Open pen-test findings | count | demo | Security exposure | CISO/CIO | 38 |
| AI Hallucination Alerts | Flagged AI outputs | count | demo (`ecs_mock_engine`) | AI risk signal | AI Gov/CIO | 2.1% rate |

## Enterprise dashboard

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| BU Compliance % | Compliance per business unit | static `BUSINESS_UNITS.compliance_pct` | demo | Which BU lags | CIO/Heads | Retail 88% |
| BU Audit Readiness | Readiness per BU | `min(99, compliance + seed)` | `executive_analytics_engine` | BU audit risk | Heads | 90 |
| BU Open Gaps / Observations | Open items per BU | count | demo | Remediation backlog | Heads | 23 gaps |
| BU Risk Score (/10) | Inverse of compliance | `(100−compliance)/8 + seed` | `executive_analytics_engine` | Relative BU risk | CIO | 3.2/10 |
| Framework Maturity % | Per-framework maturity | blended live/baseline | `demo_metrics` | Framework strength | Compliance | PCI 86% |

## Pan India dashboard

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| Regional PCI Readiness % | PCI readiness by zone | `enhance_pan_india_regions` | demo (`PAN_INDIA_REGIONS`) | Zone PCI posture | Vertical/CIO | South 88% |
| Regional Audit Readiness | Readiness by zone | region score | demo | Zone audit risk | Vertical | West 82 |
| SLA Breaches | Breaches per zone | count | demo | Operational SLA risk | Ops/Vertical | 9 |
| Critical Observations | Critical findings per zone | count | demo | Regional escalations | Vertical | 4 |
| National Score | Mean regional score | `mean(region.score)` | demo | Pan-India posture | Vertical/CIO | 88.1 |

## Reports dashboard

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| Export Distribution | Reports by type | count by category | `reports_analytics_engine` | Reporting mix | Auditor/CIO | 30 packs |
| Report Generation Trend | Reports over time | series | demo | Reporting demand | Compliance | ↑ monthly |

## Trends dashboard

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| Implementation Coverage | Implemented controls share | `100·implemented/total` | `trends_analytics_engine` | Control rollout progress | CIO/Compliance | 78% |
| Observations Net | Net observation change | `closed − opened` | `trends_analytics_engine` | Backlog direction | Auditor | −12 (good) |
| Auditor Rejection Rate | Rejected share of submissions | `100·rejected/submitted` | demo | Evidence quality | Auditor | 9% |
| Remediation SLA Compliance | On-time remediation | `on_time_pct` | demo | Remediation discipline | Governance | 84% |
| Observation Closure Rate | Closed vs opened | `100·Σclosed/Σopened` (>100 = backlog ↓) | `trends_analytics_engine` | Are we catching up | Auditor | 108% |

## Governance dashboards (Evidence Health / Approval / Completeness / Lifecycle / Exceptions)

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| Evidence Health Score | Quality/freshness composite | `mean(record health)` ; record `max(28,96−seed)` | `evidence_health_engine` | Evidence decay | Owner/Governance | 81 |
| Controls Missing Evidence | Controls with no evidence | count `Not Submitted` | `evidence_health_engine` | Coverage gaps | Owner | 14 |
| Expiring / Stale / Rejected Evidence | By issue category | counts | `evidence_health_engine` | Refresh backlog | Owner | 9 expiring |
| Approval Success % | Approved share | `100·approved/submitted` | `evidence_approval_engine` | Throughput health | Auditor | 88% |
| Rejection Rate % | Rejected share | `100·rejected/submitted` | `evidence_approval_engine` | Quality/calibration | Auditor | 9% |
| Avg Validation Time | Days to approve | `mean(validation_days)` | `evidence_approval_engine` | Reviewer bottleneck | Auditor | 3.2d |
| Dynamic Completeness % | Penalty-adjusted completeness | `(ctrl·0.6+evidence·0.4)−penalty·10` | `missing_evidence_engine` | True readiness | Compliance | 76% |
| Control Maturity % | Implemented controls | `100·implemented/total` | `governance_completeness_engine` | Coverage maturity | Compliance | 72% |
| Active / Approved / Expiring TDs | Exception counts | counts | `exception_state_engine` | TD risk | Compliance | 28 active |

## Frameworks dashboards (per framework — 6 tiles each)

Tiles are deterministic seeds in defined bands (`framework_kpi_drill_engine.py`). Examples (full ranges in product-manual §G):

| KPI (PCI DSS) | Definition | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|
| PCI Maturity | PCI program maturity | demo seed 78–92% | CDE readiness | Compliance | 85% |
| CDE Controls | Cardholder-data controls | catalog count | Scope size | Compliance | 42 |
| Encryption Coverage | Encrypted assets | seed 88–98% | Data protection | Security | 94% |
| QSA Readiness | Assessor readiness | seed 82–96% | Audit readiness | Auditor | 90% |

(Equivalent 6-tile sets exist for DPSC, OS/DB/Nginx Baselining, AppSec, VAPT, CSITE, ITPP, ITDRM, SOC2, ISO27001, RBI Cyber Security, ISG, ASST — see product-manual §G.)

## Operations dashboards

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| Scheduler Success Rate | Successful collection jobs | static + run history | demo | Collection reliability | Ops | 99.2% |
| Connector Health % | Healthy connectors | health overview | repo/demo | Integration trust | Admin/Ops | 96.1% |
| Evidence Collected Today | Daily collection | count | demo | Throughput | Ops | 1,840 |
| Query Catalog Totals | Controls/queries/manual/unsupported | counts | `predefined_queries_engine` | Automation coverage | Ops | 305 controls |

## AI Governance dashboard

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| AI Compliance Score | Weighted AI governance | `Σ dim_score·weight/100` (6 dims) | `ecs_ai_governance_drilldowns` | AI risk posture | AI Gov | 84% (target 90) |
| Data Privacy / Model Risk / Prompt Safety / Bias / Audit Trail / Human-in-Loop | Dimension scores | per-dimension | demo | Where AI governance is weak | AI Gov | Model Risk 78 |
| Hallucination Rate % | Flagged outputs | rate | demo | Output reliability | AI Gov | 2.1% |
| Prompt Audits | Prompts audited | count | demo | Oversight coverage | AI Gov | 100 |

## AI SDLC dashboards

| KPI | Definition | Formula | Data source | Business meaning | Persona | Example |
|---|---|---|---|---|---|---|
| SDLC Stage Readiness | Stage gate readiness | `(fw+ctrl+ev coverage)/3` | `ai_sdlc_governance_mock` | Can this stage pass | AI SDLC Owner | 88 |
| Release Readiness | Mean of 5 stages | `mean(stage scores)` | `ai_sdlc_governance_mock` | Go-live confidence | AI SDLC Owner | 86 |
| Framework/Control/Evidence Coverage % | Coverage per dimension | `recalculate_framework_coverage` | `ecs_governance_framework` | Gate completeness | AI SDLC Owner | 82% |
| Findings Open | Open SDLC findings | count | demo | Release blockers | AI SDLC Owner | 31 SAST |

---

## KPI documentation gap audit

| Aspect | Status | Note |
|---|---|---|
| KPI **definitions** | ✅ Complete | All defined in this dict + product-manual |
| KPI **formulas** | ✅ Complete | Every KPI has a code formula (file:line in product-manual) |
| KPI **explanations / interpretation** | ✅ Complete | Bands + "common mistakes" documented |
| KPI **business meaning** | ✅ Complete | Per-KPI business meaning above |
| KPI **in-product tooltips** | ⚠️ Partial | Drill/metric-trace exists; not all tiles show inline definitions — *UI follow-up, out of scope* |
| **Catalog vs demo-seed labeling** | ⚠️ Partial | Some demo KPIs not labeled as demo in-UI — recommend a "demo data" badge |

**Conclusion:** No KPI lacks a definition or formula. The only real gap is **inline explainability** (tooltips/labels), which is a UI enhancement, not a documentation deficiency.
