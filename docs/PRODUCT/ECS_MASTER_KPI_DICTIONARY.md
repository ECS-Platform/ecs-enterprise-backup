# ECS Master KPI Dictionary

**Type:** Master KPI reference. **No code/UI/DB changes.** **Grounding:** dashboard engines (`demo_metrics`, `executive_analytics_engine`, `trends_analytics_engine`, `evidence_health_engine`, `evidence_approval_engine`, `governance_completeness_engine`, `framework_kpi_drill_engine`, `ecs_ai_governance_drilldowns`, `ecs_platform/governance.py`). Builds on [audit KPI dictionary](../AUDIT/ECS_KPI_DICTIONARY.md) and [product-manual KPI dictionary](../product_manual/ECS_KPI_DICTIONARY.md) — this version adds **Refresh Frequency · Business Impact · Executive Usage · Associated Dashboard/Workflow/Framework** per KPI.

> **Refresh model:** Demo mode = deterministic seeds (computed per request, effectively "real-time" but synthetic). Real mode = computed from the PostgreSQL evidence repository on page load / API call (no async cache); connector-sourced inputs refresh on **scheduler** runs. ROI inputs refresh from `config/roi.yaml`. Bands: Good ≥80 · Warn 55–79 · Critical <55 (Completeness 80/65; Audit Prep 75).

---

## Legend
Each KPI: **Definition · Formula/Calculation · Data Source · Refresh · Interpretation (Good/Bad) · Business Impact · Executive Usage · Dashboard · Workflow · Framework.**

## 1. Composite readiness

### Audit Readiness Score
- **Definition:** Overall audit preparedness. **Formula:** `0.5·coverage% + 0.3·approval% + 0.2·freshness%`. **Calculation:** weighted blend per app/framework. **Data Source:** `governance.py` (repo) / demo. **Refresh:** on load / scheduler. **Good:** ≥80 (Audit Ready) · **Bad:** <55 (High risk). **Business Impact:** predicts audit pass/fail. **Executive Usage:** headline CIO metric. **Dashboard:** CIO, Platform Audit Readiness. **Workflow:** Audit preparation. **Framework:** all.

### AI Compliance Score
- **Definition:** AI governance posture. **Formula:** `Σ dimension·weight/100` over 6 dims (Data Privacy, Model Risk, Prompt Safety, Bias, Audit Trail, Human-in-Loop). **Data Source:** `ecs_ai_governance_drilldowns`. **Refresh:** on load. **Good:** ≥90 target · **Bad:** <75. **Impact:** AI risk exposure. **Exec Usage:** AI risk to board. **Dashboard:** AI Governance. **Workflow:** AI SDLC review. **Framework:** AI Governance.

## 2. Compliance & coverage

### Enterprise Compliance %
- **Definition:** Approved controls share. **Formula:** `100·approved/total` (demo floor 84.6%). **Data Source:** `ecs_state`/demo. **Refresh:** on load. **Good:** ≥85 · **Bad:** <70. **Impact:** org compliance posture. **Exec:** board KPI. **Dashboard:** CIO/Enterprise. **Workflow:** Control validation. **Framework:** all.

### Control Coverage % / Control Maturity %
- **Definition:** Controls with sufficient evidence / implemented. **Formula:** `100·covered(implemented)/total`. **Source:** `governance.py`, completeness engine. **Refresh:** on load / scheduler. **Good:** ≥80 · **Bad:** <55. **Impact:** audit gap size. **Exec:** coverage trend. **Dashboard:** Completeness, Platform Coverage. **Workflow:** Control validation. **Framework:** all.

### Framework Coverage % / Maturity %
- **Definition:** Per-framework covered controls / maturity. **Formula:** `covered/expected` per framework. **Source:** `framework_coverage()`, `demo_metrics`. **Refresh:** on load. **Good:** ≥80 · **Bad:** <55. **Impact:** regulation readiness. **Exec:** per-regulation posture. **Dashboard:** Framework page, Enterprise. **Workflow:** Control validation. **Framework:** specific.

### Dynamic Completeness %
- **Definition:** Penalty-adjusted completeness. **Formula:** `(ctrl·0.6 + evidence·0.4) − penalty·10`. **Source:** `missing_evidence_engine`. **Refresh:** on load. **Good:** ≥80 · **Bad:** <65. **Impact:** true readiness. **Exec:** realistic readiness. **Dashboard:** Completeness. **Workflow:** Control validation. **Framework:** all.

## 3. Evidence quality

### Evidence Health Score
- **Definition:** Quality/freshness composite. **Formula:** `mean(record health)`, record `max(28, 96−seed)`. **Source:** `evidence_health_engine`. **Refresh:** on load / scheduler. **Good:** ≥80 · **Bad:** <55. **Impact:** decay risk. **Exec:** evidence trust. **Dashboard:** Evidence Health. **Workflow:** Evidence lifecycle. **Framework:** all.

### Controls Missing Evidence / Expiring / Stale / Rejected
- **Definition:** Counts by issue. **Formula:** counts by status/age. **Source:** `evidence_health_engine`. **Refresh:** on load. **Good:** lower · **Bad:** rising. **Impact:** remediation backlog. **Exec:** gap watch. **Dashboard:** Evidence Health. **Workflow:** Evidence lifecycle. **Framework:** all.

### Approval Success % / Rejection Rate % / Avg Validation Time
- **Definition:** Reviewer throughput/quality/speed. **Formula:** `approved/submitted`, `rejected/submitted`, `mean(days)`. **Source:** `evidence_approval_engine`. **Refresh:** on load. **Good:** ≥85 / <10 / <3d · **Bad:** <70 / >20 / >7d. **Impact:** review bottleneck. **Exec:** SLA health. **Dashboard:** Evidence Approval. **Workflow:** Evidence approval. **Framework:** all.

## 4. Reuse & efficiency

### Evidence Reuse % / Reuse Factor
- **Definition:** Collect-once-reuse-many. **Formula:** `reused/mappings`, `mappings/artifacts`. **Source:** `evidence_reuse()`, `framework_intelligence`. **Refresh:** on load. **Good:** higher. **Impact:** collection-cost savings. **Exec:** ROI driver. **Dashboard:** Reuse, Platform Evidence Reuse. **Workflow:** Control validation. **Framework:** cross-framework.

## 5. Trends

### Implementation Coverage / Observations Net / Closure Rate / Rejection Rate / SLA Compliance
- **Definition:** Rollout / backlog direction / catch-up / quality / on-time. **Formula:** `implemented/total`, `closed−opened`, `Σclosed/Σopened`, `rejected/submitted`, `on_time/total`. **Source:** `trends_analytics_engine`. **Refresh:** on load (period filter). **Good:** ≥80 / negative / >100% / <10 / ≥85 · **Bad:** inverse. **Impact:** trajectory/early-warning. **Exec:** trend story. **Dashboard:** Trends. **Workflow:** Audit prep. **Framework:** all.

## 6. Enterprise & regional

### BU Compliance % / BU Risk Score / BU Audit Readiness
- **Formula:** per-BU compliant; `(100−compliance)/8`; `min(99, compliance+seed)`. **Source:** `executive_analytics_engine` (`BUSINESS_UNITS`). **Refresh:** on load. **Good:** ≥85 / low / ≥85. **Impact:** BU accountability. **Exec:** BU drilldown. **Dashboard:** Enterprise. **Workflow:** Comparison. **Framework:** all.

### Regional Readiness % / SLA Breaches / Critical Observations / National Score
- **Formula:** per-region score; counts; `mean(region.score)`. **Source:** `executive_analytics_engine` (`PAN_INDIA_REGIONS`). **Refresh:** on load. **Good:** ≥85 / lower / lower / ≥85. **Impact:** regional posture. **Exec:** Pan-India view. **Dashboard:** Pan India. **Workflow:** —. **Framework:** all.

## 7. Operations

### Scheduler Success Rate / Connector Health % / Evidence Collected Today
- **Formula:** `success/runs`, `healthy/total`, count. **Source:** `scheduler_intelligence`, `health_overview()`. **Refresh:** per scheduler run. **Good:** ≥98 / ≥95 / steady. **Impact:** collection reliability. **Exec:** automation trust. **Dashboard:** Scheduler, Integration Health. **Workflow:** Evidence collection. **Framework:** all (query-driven).

### Query Catalog Totals (Controls/Queries/Manual/Unsupported)
- **Formula:** counts from `predefined_queries_engine`. **Refresh:** on load. **Impact:** automation coverage. **Dashboard:** Predefined Queries. **Workflow:** Evidence collection. **Framework:** OS/DB/Nginx/AppSec.

## 8. AI SDLC

### SDLC Stage Readiness / Release Readiness / Coverage % / Findings Open
- **Formula:** `(fw+ctrl+ev coverage)/3`; `mean(stage scores)`; coverage; counts. **Source:** `ai_sdlc_governance_mock`, `ecs_governance_framework`. **Refresh:** on load. **Good:** ≥85 / ≥85 / ≥80 / lower. **Impact:** go-live confidence. **Exec:** AI delivery posture. **Dashboard:** AI SDLC Control Tower. **Workflow:** AI SDLC review. **Framework:** AI Governance / AI-SDLC.

## 9. Risk & AI governance

### Open VAPT / Hallucination Rate % / Prompt Audits
- **Formula:** counts / rate / count. **Source:** demo, `ecs_mock_engine`, posture. **Refresh:** on load. **Good:** lower / <3% / higher coverage. **Impact:** security + AI risk. **Exec:** risk to board. **Dashboard:** CIO, AI Governance. **Workflow:** Risk management. **Framework:** VAPT, AI Governance.

## 10. ROI

### Annual Value / Hours Saved / FTE Equivalent / Payback / ROI %
- **Formula:** from `config/roi.yaml` via `roi/workbook.py` (hours × rate; reuse savings). **Refresh:** on config change. **Good:** higher / shorter payback. **Impact:** investment justification. **Exec:** the money slide. **Dashboard:** ROI Center. **Workflow:** ROI measurement. **Framework:** all.

---

## Cross-references
- Audit-grade gap analysis: [ECS_KPI_DICTIONARY.md (AUDIT)](../AUDIT/ECS_KPI_DICTIONARY.md)
- Quick talk-track bands: [ECS_KPI_REFERENCE.md (TRAINING)](../TRAINING/ECS_KPI_REFERENCE.md)
- Formula file:line anchors: [product_manual/ECS_KPI_DICTIONARY.md](../product_manual/ECS_KPI_DICTIONARY.md)
- Screens that show each KPI: [ECS_MASTER_PRODUCT_MANUAL.md](ECS_MASTER_PRODUCT_MANUAL.md)

> **Caveat:** demo KPIs are deterministic synthetic seeds, not live measurements. Catalog vs demo-seed counts differ — state which when quoting.
