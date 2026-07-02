# ECS KPI Dictionary & Chart Guide

Part of the **ECS Product Operations Manual** (Sections 5 & 6). Every KPI visible in ECS, with formula, source, interpretation, and thresholds — plus the chart guide. All formulas are quoted from the actual engines with file:line citations.

> **Read this first — demo vs live.** ECS computes many KPIs two ways: a **live path** against the PostgreSQL repository (`ecs_platform/governance.py`) and a **deterministic demo path** (`ecs_platform/demo_governance.py`, `modules/.../demo_metrics.py`, framework KPI seeds). Executive dashboards often **blend** live values with seeded baselines (e.g. floor enterprise compliance at 84.6%). Framework-page KPI tiles are **deterministic seeds** (MD5 of `framework::metric`), not live connector math. Flag-gated engines (sufficiency, observation readiness, portfolio) return neutral values unless their env flag is on. These behaviors are intentional for demo determinism.

---

## Global threshold bands

Reused across the UI for color/labels:

| Band / concept | Thresholds | Source |
|---|---|---|
| Audit readiness band | Ready ≥80%, At Risk ≥55%, Not Ready <55% | `ecs_platform/governance.py:567`, `demo_governance.py:246` |
| Audit Prep readiness split | good/warning at **75%** (`READINESS_THRESHOLD`) | `audit_prep_data.py:14,364` |
| Heatmap cell tone | ≥85 green · 75–84 amber · 65–74 red · <65 dark-red | `executive_analytics_engine.py:174,242` |
| Completeness audit risk | High <65% · Medium <80% · else Low | `governance_completeness_engine.py:91` |
| Application compliance risk | High <50% · Medium <80% · Low otherwise | `analytics_module.py:66` |
| Sufficiency score band | Ready ≥80 · At Risk ≥55 · Not Ready <55 | `sufficiency/rules.py:175` |
| Observation closure readiness | Ready ≥80 · Nearly Ready ≥55 · else Not Ready (+ hard blockers) | `evidence_intel/readiness.py:31,141` |
| Quality score label | Complete ≥85 · Partial ≥70 · else Incomplete | `evidence_approval_engine.py:46` |

---

# Part 1 — KPIs

## A. Composite (weighted) scores

### A1 · Audit Readiness Score (platform)
- **Location:** `/mvp/platform/audit-readiness`, Executive Summary, Role Scorecard, CIO dashboards
- **Business meaning:** Overall preparedness for an audit review.
- **Formula:** `score = 0.5 × coverage_pct + 0.3 × approval_pct + 0.2 × fresh_pct` (`ecs_platform/governance.py:552-565`)
  - **coverage_pct** = `100 × covered_controls / total_controls` (numerator: controls with ≥1 evidence; denominator: catalog controls)
  - **approval_pct** = approved evidence / total reviews
  - **fresh_pct** = `100 × (total_reviews − expired) / total_reviews`
- **Per-application (live):** `0.6 × control_pct + 0.4 × approval_pct` (`governance.py:593`); **demo:** same weights (`demo_governance.py:231,245`)
- **Source data:** evidence repository control/evidence/review counts (demo fallback when no DB)
- **Interpretation / bands:** **90–100 Audit Ready · 70–89 Needs Attention · <70 High Audit Risk** (band labels Ready ≥80 / At Risk ≥55 / Not Ready <55 in code)
- **Related:** Control Coverage, Evidence Approval %, Stale Evidence %

### A2 · Dynamic Completeness % (Audit Readiness, Completeness module)
- **Location:** `/mvp/completeness` KPI strip
- **Formula:** `clamp(0,98, (ctrl_score×0.6 + evidence_score×0.4) − penalty×10)` (`missing_evidence_engine.py:311-327`)
  - **ctrl_score** = `100 × implemented / total_controls`
  - **evidence_score** = `100 × (uploaded + approved×1.2) / total`
  - **penalty** = `(missing×0.15 + overdue×0.25 + rejected×0.1) / total`
- **Interpretation:** higher = more complete; capped at 98. <65 high audit risk (per completeness band).
- **Related:** Control Maturity, Audit Readiness

### A3 · SDLC Stage / Release Readiness (AI SDLC)
- **Location:** AI SDLC stage worklists, Control Tower, Go-Live, Governance Quality
- **Framework row score:** `ctrl_pct×0.35 + map_pct×0.25 + ev_pct×0.25 + attach_pct×0.15` (`ecs_governance_framework.py:122-148`)
- **Stage readiness:** `(fw_coverage + ctrl_coverage + ev_coverage) / 3` (`ai_sdlc_governance_mock.py:435`)
- **Release readiness:** mean of the 5 stage scores (`ai_sdlc_governance_mock.py:1226,1413`)
- **Interpretation:** Go-Live gate typically expects ≥ readiness band (≥80 ready).

### A4 · AI Compliance Score
- **Location:** `/mvp/ai-governance` (AI Governance Posture)
- **Formula:** `Σ (dimension_score × weight_pct / 100)` (`ecs_ai_governance_drilldowns.py:78-91`)
- **Dimension weights:** Data Privacy 18 · Model Risk 20 · Prompt Safety 18 · Bias & Fairness 16 · Audit Trail 14 · Human-in-Loop 14 (`:27-63`)
- **Target:** 90% · **Interpretation:** below target → governance gaps in the lowest-contributing dimensions.

### A5 · Evidence Sufficiency Score *(flag-gated `SUFFICIENCY_ENGINE_ENABLED`)*
- **Formula:** `Σ dimension.score × weight` (`app/sufficiency/engine.py:164`)
- **Weights:** completeness 30% · freshness 25% · traceability 20% · coverage 15% · review 10% (`sufficiency/rules.py:171`)
- **Bands:** Ready ≥80 · At Risk ≥55 · Not Ready <55

### A6 · Observation Closure Readiness *(flag-gated `OBSERVATION_READINESS_ENABLED`)*
- **Formula:** `Σ factor × weight` (`app/evidence_intel/readiness.py:133`)
- **Weights:** evidence_present 25 · evidence_approved 25 · remediation_attached 15 · observation_age 10 · control_coverage 15 · unresolved_dependencies 10
- **Levels:** Ready ≥80 · Nearly Ready ≥55 · else Not Ready; a non-empty `blocking` list forces Not Ready.

### A7 · ROI Audit Readiness Score
- **Location:** `/mvp/roi`
- **Formula:** `min(99, 70 + total_frameworks)` (`app/roi/workbook.py:644`)

---

## B. Coverage / compliance / maturity

| KPI | Location | Formula | Source / lines |
|---|---|---|---|
| **Enterprise Compliance %** | CIO, enterprise | `100 × approved / total` (live control statuses); display `max(live, 84.6)` floor | `ecs_state.py:220`, `demo_metrics.py:281` |
| **Implementation Coverage** | Trends, Governance Analytics | `100 × implemented / total`; enterprise base 58,563 controls; blend `max(live, base×0.35+live×0.65)` | `trends_analytics_engine.py:65` |
| **Control Coverage %** | Platform control-coverage | `100 × covered / total_controls` (covered = catalog control w/ ≥1 evidence) | `governance.py:317` |
| **Framework Coverage %** | Platform framework-coverage | per fw `100 × covered / expected` via crosswalk | `governance.py:336` |
| **Control Maturity %** | Completeness | `100 × Σimplemented / Σtotal_controls` | `governance_completeness_engine.py:131` |
| **Per app×fw readiness** | Completeness detail | seed `min(98, 52 + s%44)`; implemented = total×readiness/100 | `governance_completeness_engine.py:26` |
| **Application compliance %** | Comparison | `100 × approved / total` per app | `analytics_module.py:65` |
| **Control validation effectiveness %** | Validation | `100 × passed / total_checks` | `control_validation_engine.py:316` |
| **ITPP DR readiness %** | ITPP | `100 × approved_dr / dr_controls` | `control_validation_engine.py:405` |
| **National / Pan-India score** | Pan India, vertical | `mean(region.score)` | `demo_metrics.py:288`, `analytics_module.py:123` |
| **Business-Unit compliance %** | Enterprise | static `BUSINESS_UNITS.compliance_pct` | `demo_metrics.py:61` |
| **BU audit readiness** | Enterprise | `min(99, compliance + seed(−2..+4))` | `executive_analytics_engine.py:62` |
| **BU risk score (/10)** | Enterprise | `(100−compliance)/8 + seed`, clamp 1–10 | `executive_analytics_engine.py:63` |
| **Audit Prep weighted readiness** | Audit Prep | `mean(readiness_pct)` across filtered apps | `audit_prep_data.py:314` |
| **Audit Prep matrix cell** | Audit Prep heatmap | `(fw_readiness + app_readiness)/2 + seed(−5..+5)` | `executive_analytics_engine.py:194` |
| **Comparison matrix readiness** | Comparison | `min(98, 55 + seed%38)` | `comparison_engine.py:47` |
| **Evidence reuse %** | Reuse, scorecard | static demo 34.5%; live: multi-control evidence + crosswalk fan-out | `demo_metrics.py:69`, `governance.py:218` |
| **Scheduler success rate %** | Scheduler | static 99.2% + run history | `demo_metrics.py:77` |

**Interpretation guidance:** all coverage/compliance/maturity KPIs are 0–100% where higher is better; apply the global readiness band (≥80 good / 55–79 watch / <55 critical) unless a module states otherwise (Completeness uses 80/65; Audit Prep uses 75).

---

## C. Evidence health / approval / workflow

### Evidence Health (`/mvp/evidence-health`, `evidence_health_engine.py`)
| KPI | Formula | Lines |
|---|---|---|
| Health Score | `mean(record health_score)` over first 60 scoped records | 207 |
| Record health_score | `max(28, 96 − seed)` capped by risk tier | 92 |
| Controls Missing Evidence | count `validation_status == "Not Submitted"` | 208 |
| Evidence w/ Open Observations | count with `observation_id` | 209 |
| High-Risk Failures | count risk Critical/High | 215 |
| Expiring / Rejected / Revalidated / Stale | counts by issue category | 216-219 |

**Interpretation:** Health Score is 0–100 (higher better). Rising "Missing/Expiring/Rejected" counts signal degrading audit posture.

### Evidence Approval (`/mvp/evidence-approval`, `evidence_approval_engine.py`)
| KPI | Formula | Lines |
|---|---|---|
| Approval Success % | `100 × approved / total_submitted` | 151 |
| Rejection Rate % | `100 × rejected / total_submitted` | 152 |
| Avg Validation Time (days) | `mean(validation_days)` for approved | 153 |
| Framework approval % | per-fw approved/rows ×100 | 165 |
| Application maturity % | per-app approved/rows ×100 | 178 |
| Quality score | seed 62–98 by name+status | 42 |

**Interpretation:** Approval Success % high & Rejection Rate % low is healthy. Long Avg Validation Time indicates reviewer bottlenecks.

### Workflow / exceptions / lifecycle (counts)
| KPI | Where | Source |
|---|---|---|
| Approval rate | workflow | `100 × approved / (approved+rejected+pending)` (`evidence_workflow_engine.py:202`) |
| Missing/Critical/Overdue uploads, Audit-closure impact | Completeness/Upload | `missing_evidence_engine.py:295` |
| Active / Approved TDs / Rejected / Expiring / High-Risk Open / Pending Review | Exception Governance | `exception_state_engine.py:213` |
| Control Lifecycles, Evidence Records, Open Observations, Active Remediations, Audit Cycles, Active Exceptions | Lifecycle | `governance_lifecycle_engine.py:390` |

---

## D. Trends executive KPIs (`trends_analytics_engine.py:219-262`)

| KPI | Formula |
|---|---|
| Implementation Coverage | `totals.coverage_pct` (implemented/total) |
| Observations Net | `closed − opened` (latest month) |
| Auditor Rejection Rate | latest `rejected/submitted × 100` (`:169`) |
| Remediation SLA Compliance | latest `on_time_pct` (`:187`) |
| Observations closure rate (period) | `100 × Σclosed / Σopened` — **>100% = backlog reduction** (`:276`) |

---

## E. Role dashboard KPI strips (`demo_metrics.py:131-302`)

Per-role strips (representative demo values):

| Role | Headline KPIs |
|---|---|
| Auditor | auditor pending queue, approvals today = 14 |
| Owner | pending tasks, resubmits required, applications owned, open observations, SLA breaches = 9, audit readiness = 83.5% |
| Compliance Head | audit readiness = 86.2% |
| Vertical Head | national score = 88.1 |
| CIO | enterprise compliance, evidence artefacts, audit completion = 91.6% |
| Functional Head | audit readiness = 82.4% |
| Security Officer | critical vulns = 12, VAPT open = 38, MTTR = 6.4d, security score = 79.5 |
| Operations Owner | collection jobs today = 142, failed jobs = 7, connector health = 96.1%, evidence collected = 1840 |
| Platform Ops | active connectors = 12, sync runs = 53, uptime = 99.7% |
| Governance Lead | open risks = 46, high/critical = 11, exceptions active = 28, governance score = 84.0 |
| Framework Owner | frameworks owned = 4, control coverage = 81.7%, open gaps = 23 |
| AI Governance Owner | AI systems = 18, prompt audits = 100, hallucination rate = 2.1%, AI risk = 77.4 |
| AI SDLC Owner | apps in SDLC = 26, gates passed = 84, SAST open = 31, release readiness = 88.0% |

**Enterprise KPIs object** (`enterprise_kpis()`): enterprise compliance %, national score, open/closed/rejected observations, audit readiness = 86.2%, reuse = 34.5%.

---

## F. Demo Overview tiles (`ecs_mock_engine.py:817-828` / CIO strip `:767-776`)

Banking Applications · Frameworks · Controls (Σ control_count) · Evidence Records · ServiceNow Tickets · AI Prompts Audited · Hallucination Alerts · Open VAPT · Critical Drift · 5-Yr Avg Closure. CIO strip: Enterprise Readiness = `mean(audit_readiness_pct)`, Frameworks Live, Apps In Scope, Open VAPT, AI Hallucination Alerts, Drift Critical, Audit Closure Velocity, Regulator Readiness (Green if readiness ≥80).

---

## G. Framework-page KPI tiles (6 per framework)

**Engine:** `framework_kpi_drill_engine.py` — values are deterministic seeds (MD5 of `framework::metric`); `pct` returns a random int in the band, `ctrl`=control count, `evidence`=evidence total, `stale`=stale+expired (`:159-171`).

| Framework | KPI tiles (range) |
|---|---|
| **PCI DSS** | PCI Maturity 78–92% · CDE Controls (count) · Encryption Coverage 88–98% · MFA Exceptions 0–4 · Open Audit Gaps 2–9 · QSA Readiness 82–96% |
| **DPSC** | Payment Controls 18–42 · UPI Security 12–28 · Card Security 10–24 · Encryption Compliance 91–99% · Open Payment Findings 3–14 · Retention Violations 1–6 |
| **OS Baselining** | Servers Assessed 840–1240 · Baseline Deviations 18–56 · Critical Deviations 4–16 · Patch Compliance 84–96% · Hardening Score 79–93% · Unsupported OS 2–9 |
| **DB Baselining** | DBs Assessed 62–118 · Critical Findings 3–12 · Privilege Violations 2–11 · Backup Compliance 88–98% · Encryption Coverage 91–99% · Audit Logging Gaps 1–5 |
| **Nginx Baselining** | TLS Posture 86–97% · Expired Certs 1–6 · Weak Ciphers 2–8 · Internet Exposure 4–14 · Config Drifts 6–22 · WAF Coverage 78–94% |
| **AppSec** | SAST Open 14–38 · DAST Critical 3–12 · SCA Vulns 8–28 · Release Blockers 1–7 · Secure SDLC Score 72–89% · Vulnerable Apps 4–9 |
| **VAPT** | Open Vulns 18–52 · Critical CVEs 2–11 · Pen-Test Findings 6–24 · Remediation Backlog 8–28 · Retest Pass Rate 78–94% · Internet Findings 5–19 |
| **CSITE** | SAST 10–32 · DAST 6–22 · Code Review Coverage 74–92% · Secure Coding Controls 24–58 · Remediation Progress 62–88% · Reopened Findings 1–5 |
| **ITPP** | Policies Reviewed 28–48 · Process Controls 42–86 · Exceptions 3–14 · Compliance 85–96% · Open Actions 5–22 · DR Test Compliance 88–98% |
| **ITDRM** | IT Risks 14–38 · DR Test Coverage 82–96% · BCP Gaps 3–12 · Critical IT Dependencies 4–15 · Open DR Actions 6–20 · RTO Breaches 1–5 |
| **SOC2** | Trust Criteria Coverage 86–97% · Access Control Tests 32–68 · Change Mgmt Gaps 2–10 · Availability SLAs 99–100% · Open Observations 3–14 · Evidence Gaps 2–9 |
| **ISO27001** | Annex A Controls 78–114 · ISMS Maturity 80–94% · Risk Treatment Gaps 4–16 · Non-Conformities 1–8 · SoA Coverage 88–99% · Corrective Actions 3–12 |
| **RBI Cyber Security** | RBI Maturity 74–88% · Incident Reporting Gaps 2–9 · API Security Controls 8–22 · Cyber Resilience 79–93% · Third-Party Risk Gaps 4–14 · Board Reporting Readiness 82–96% |

*(ISG and ASST use the same engine pattern; their tiles follow the framework's configured KPI set.)*

**Interpretation:** "% / score / coverage / readiness" tiles — higher is better, apply the global band. "Findings / gaps / exceptions / deviations / breaches" tiles — lower is better; rising counts are negative.

---

## H. AI SDLC / onboarding KPIs
- Framework readiness (onboarding): static `coverage_pct` per framework (`ai_sdlc_onboarding_engine.py:43`)
- Policy compliance aggregate: `mean(policies.compliance_pct)` (`ecs_ai_governance_drilldowns.py:124`)
- AI evidence coverage: `collected/required×100`; approval `approved/max(collected,1)×100` (`:291`)
- AI SDLC report compliance %: `complete/total×100` (`ai_sdlc_reports_engine.py:80`)

## I. Platform scorecard (`demo_governance.py:285-291`)
applications · evidence_collected · evidence_reuse_pct · framework_reuse_ratio · framework_ops_saved · framework_coverage_pct · control_coverage_pct · open_observations · rejected_evidence · compliance_score (= audit readiness).

## J. Predefined queries / onboarding / loader
- Query catalog: Total Controls · Predefined Queries · Manual Controls · Frameworks Covered · Unsupported Tech (`predefined_queries_engine.py:474`)
- Framework onboarding: Onboarded · Active · Pending Review · Controls Imported (`framework_onboarding_engine.py:571`)

## K. Governance QA (`ecs_governance_qa_engine.py`)
- data_completeness % = `resolved/total×100` · governance_readiness % = `mean(stage.readiness_score)` · validation % = `passed/checks×100`

---

# Part 2 — Chart guide

**Rendering systems (no Chart.js):** all charts are CSS bars, SVG sparklines, or HTML heatmap grids governed by `executive_charts_system.html` + accessibility tokens in `ecs_chart_standard.html`.

| Renderer | Type | Notes | Lines (executive_charts_system.html) |
|---|---|---|---|
| `ecsRenderCompactBarChart` | Vertical bars | auto `niceScale()`, optional benchmark line, trend pill, drill attrs | 521-687 |
| `ecsRenderHorizontalBars` | Horizontal progress | width = value/max×100 | 690-709 |
| `ecsRenderSparkline` | SVG line | min–max normalized | 713-736 |
| CSS `.trend-chart` | Inline height bars | server-rendered intel series | governance/trends templates |
| `.ecs-heatmap-tile` / table heatmaps | Heatmap grid | tone from score thresholds | analytics templates |
| `.ecs-exec-donut` | CSS conic donut | micro 48×48 | exec templates |

**Default axes** (when `ecsRenderCompactBarChart` defaults apply): **X** = category labels (`xLabel`, default "Category"); **Y** = auto-scaled value (`yLabel`, default "Value"/"Value (%)"). Data source = inline JSON from Jinja `|tojson` or async filter refresh.

### Charts by screen (for each: what it measures · X · Y · data source)

**Enterprise** (`mvp_enterprise.html`): Compliance % · BU · % · `BUSINESS_UNITS.compliance_pct`. Audit Readiness · BU · % · derived. Open Gaps / Observations · BU · count. Risk Score · BU · /10. Framework Maturity · framework · maturity %. Executive heatmap (horizontal) · framework · readiness %.

**Trends** (`mvp_trends.html`): Compliance Trend (granularity tabs) · period · % · `build_granularity_trends`. Observation Trend (grouped) · month · opened/closed/net. Evidence Rejections · month · count/rate. Risk Escalation · month · count. Framework Contribution (horizontal) · framework · implemented controls. Historical Trend · quarter · coverage %. Intel blocks: Implementation Coverage, Observations, Rejection Rate, SLA Compliance · month · respective metric. Aging: Evidence Aging, Remediation Velocity, Weekly Control Growth, Stale Evidence.

**Governance Analytics** (`mvp_governance_analytics.html`): Implementation Coverage / Observations / Rejection Rate intel trend blocks · month · metric · `governance_intelligence.py`.

**Pan India** (`mvp_pan_india.html`): PCI Readiness / Audit Readiness / Framework Posture · zone · % ; SLA Breaches / Critical Observations · zone · count · `enhance_pan_india_regions`.

**Evidence Health**: Rejection Trend · month · rate % ; Stale Evidence Aging · aging band · count.

**Evidence Approval**: Approval Trend · period · % ; Rejection Trend · period · count ; Framework Approval % (bar) ; Reviewer Workload (horizontal) ; Application Maturity (horizontal %) ; Stale Aging.

**Comparison**: Readiness evolution · period · % ; Failed controls trend ; Observation closure trend ; Framework maturity trend · `comparison_engine.build_trend_bundle`.

**Lifecycle**: Evidence aging by band ; Remediation velocity ; Stale evidence trend ; Exception expiry timeline ; Audit closure (gantt) · `governance_lifecycle_engine`.

**Audit Prep / Heatmaps**: framework×application readiness heatmap (cell = blended readiness, tone from `_heat_tone`); period heatmaps (month/quarter/year) for framework/app/BU/regional · `executive_analytics_engine.py:184-247`.

**Regulatory**: Coverage by Control Theme · theme · coverage % ; Framework Overlap.

**Risk Register**: Risk Severity Distribution ; Risk Aging.

**Reports**: Export Distribution ; Report Generation Trend ; Top Downloaded / Recent / Upcoming lists.

**ROI Center**: ROI bars (annual value, hours saved, FTE) · `app/roi/workbook.py` + `roi_storyboard.js`.

**Integrations Hub**: connector usage by application ; health distribution ; executive bar + sparkline.

**AI Governance Posture**: Risk heatmap (CSS grid, cell = dimension score) ; Evidence collection trend (Submitted/Approved/Rejected/Pending) · `build_ai_evidence_trend`.

**AI SDLC Control Tower**: framework×application table heatmap (cell = posture score).

**Platform Audit Readiness** (`gov_audit_readiness.html`): CSS gauge (width = composite score %) + component KPI tiles.

### How to read the charts (common guidance)
- **% bars / gauges:** apply the global band (≥80 good · 55–79 watch · <55 critical), except Completeness (80/65) and Audit Prep (75).
- **Observation closure rate:** >100% means you're closing faster than new observations open (backlog shrinking) — a *good* signal.
- **Rejection rate trend rising:** more evidence is being bounced back — investigate evidence quality or reviewer calibration.
- **Heatmap tone:** green = ready, amber = watch, red/dark-red = at risk — scan for red clusters by framework or application.
- **Common mistakes:** (1) treating framework-page tile values as live connector metrics — they are deterministic demo seeds; (2) comparing a blended executive % against a raw live % — executives are floored/blended; (3) reading "findings/gaps" bars as "higher is better" — for those, lower is better.

---

## Quick KPI → screen index

| KPI | Primary screen(s) |
|---|---|
| Audit Readiness Score | Platform Audit Readiness, Scorecard, CIO, Audit Prep |
| Enterprise Compliance % | CIO, Enterprise, Demo Overview |
| Implementation Coverage | Trends, Governance Analytics |
| Control / Framework Coverage % | Platform Control/Framework Coverage, Completeness |
| Completeness / Control Maturity % | Completeness |
| Approval Success % / Rejection Rate % | Evidence Approval, Trends |
| Evidence Health Score | Evidence Health |
| Reuse % | Evidence Reuse, Scorecard |
| AI Compliance Score | AI Governance Posture |
| SDLC Readiness | AI SDLC stages, Control Tower, Governance Quality |
| ROI value / hours / FTE | ROI Center |
| Risk severity / aging | Risk Register, Heatmaps |
| Exceptions Active / Expiring | Exceptions, Exception Governance |
| National / Pan-India score | Pan India, Vertical Head |
| Framework KPI tiles (6 each) | `/framework/{name}` |
