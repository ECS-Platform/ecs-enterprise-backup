# ECS KPI Validation Report (Phase 1)

**Mode:** READ-ONLY / ANALYSIS / REPORTING. **No KPI calculation changes. No commits.** **Grounding:** dashboard engines (`demo_metrics`, `executive_analytics_engine`, `trends_analytics_engine`, `evidence_health_engine`, `evidence_approval_engine`, `governance_completeness_engine`, `missing_evidence_engine`, `framework_kpi_drill_engine`, `ecs_ai_governance_drilldowns`, `scheduler_intelligence`, `ecs_platform/governance.py`), `roi/workbook.py` + `config/roi.yaml`, `nav_audit/executive_kpi_catalog.md`, `nav_audit/drilldown_validation_report.md`. Builds on [Master KPI Dictionary](../PRODUCT/ECS_MASTER_KPI_DICTIONARY.md) and [AUDIT KPI Dictionary](../AUDIT/ECS_KPI_DICTIONARY.md).

> **Validation scope:** confirm each KPI has a *source*, a *calculation*, *dependencies*, and *drilldowns* — without altering any formula.

---

## 1. Validation matrix (representative; full list in Master KPI Dictionary)

| KPI | Source engine | Calculation (verified, unchanged) | Dependencies | Drilldown | Status |
|---|---|---|---|---|---|
| Audit Readiness Score | `governance.py`/demo | `0.5·coverage + 0.3·approval + 0.2·freshness` | evidence, reviews, ages | app/framework | ✅ valid |
| Enterprise Compliance % | `ecs_state`/demo | approved/total (demo floor 84.6%) | control statuses | framework/BU | ✅ valid |
| Control Coverage % | `governance.py` | covered/total | evidence_control_map | control list | ✅ valid |
| Dynamic Completeness % | `missing_evidence_engine` | `(ctrl·0.6+ev·0.4) − penalty·10` | exceptions, gaps | gap list | ✅ valid |
| Evidence Health Score | `evidence_health_engine` | mean record health `max(28,96−seed)` | ages, status | expiring/stale | ✅ valid |
| Approval Success % / Rejection % / Avg Time | `evidence_approval_engine` | approved|rejected/submitted; mean days | reviews | reviewer/app | ✅ valid |
| Evidence Reuse % / Factor | `evidence_reuse()` | reused/mappings; mappings/artifacts | crosswalk | reuse map | ✅ valid |
| Trends (coverage/obs net/closure/rejection/SLA) | `trends_analytics_engine` | period rollups | observations, reviews | trend points | ✅ valid |
| BU / Regional KPIs | `executive_analytics_engine` | per BU/region seeds | BUSINESS_UNITS/PAN_INDIA_REGIONS | BU/region | ✅ valid |
| Framework KPIs (6 tiles) | `framework_kpi_drill_engine` | per-framework coverage/maturity | catalog, evidence | control drill | ✅ valid |
| Scheduler Success / Connector Health | `scheduler_intelligence`/`health_overview()` | success/runs; healthy/total | sync_runs, connectors | job/connector | ✅ valid |
| AI Compliance Score | `ecs_ai_governance_drilldowns` | Σ dim·weight/100 (6 dims) | posture dims | dimension | ✅ valid |
| AI-SDLC readiness | `ai_sdlc_governance` | mean(stage scores) | stage evidence | stage | ✅ valid |
| ROI (annual value/hours/FTE/payback) | `roi/workbook.py` | hours×rate + reuse savings | `config/roi.yaml` | scenario | ⚠ see RB-P2-01 |

Every KPI surfaced in `nav_audit/drilldown_validation_report.md` has a working drilldown (rendered evidence PNGs present in `nav_audit/drilldown_evidence/`).

## 2. Findings

### 2.1 Source/calculation integrity
All sampled KPIs trace to a deterministic engine function; no orphan KPI (displayed without a source) found. Demo values are deterministic synthetic seeds (computed per request), **not live measurements** — must be stated when quoting.

### 2.2 ROI rate-basis discrepancy (carried forward)
`config/roi.yaml` `cost_per_hour: 1500` vs ROI tables consistent with ₹1,000/hr (see [documentation audit](../../executive/documentation_audit.md)). Calculation is internally consistent but the **rate basis is ambiguous**.

### 2.3 Catalog vs demo-seed counts
Some KPIs derive from the framework catalog (305 controls) while demo dashboards show rounded seeded figures — quote the basis explicitly.

## 3. Gap classification

| ID | Finding | Severity | Recommendation (document only) |
|---|---|---|---|
| KPI-P2-01 / RB-P2-01 | ROI rate basis ambiguous (1500 vs 1000) | **P2** | Decide canonical rate in a doc + re-baseline ROI narrative; do **not** edit `roi.yaml` under this read-only mandate. |
| KPI-P3-01 | Demo vs catalog count basis not always labeled on screen | **P3** | Add a documentation note; no KPI change. |
| KPI-P3-02 | Demo KPIs are synthetic seeds | **P3** | Already documented; reinforce "demo data" labeling in talk-tracks. |

## 4. Verdict
**KPI layer: GO (with P2 ROI note).** Every KPI has verified source, calculation, dependencies, and drilldown. Only the ROI rate-basis (P2) needs a documentation decision — no calculation change permitted or required.

## Cross-references
- [Master KPI Dictionary](../PRODUCT/ECS_MASTER_KPI_DICTIONARY.md) · [AUDIT KPI Dictionary](../AUDIT/ECS_KPI_DICTIONARY.md) · [Screen Validation](ECS_SCREEN_VALIDATION_REPORT.md)
