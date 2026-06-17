# ECS KPI Reference (Knowledge Transfer)

**Audience:** anyone who must explain a number on screen — demo teams, PMs, auditors, new joiners. Quick-reference card: KPI → meaning → formula → good/warning/critical. Full audit-grade detail in `docs/AUDIT/ECS_KPI_DICTIONARY.md`; code-level formulas in `docs/product_manual/ECS_KPI_DICTIONARY.md`.

**Bands (default):** Good ≥ 80 · Warning 55–79 · Critical < 55. (Completeness 80/65; Audit Prep 75.)

---

## The 25 KPIs you must be able to explain

| KPI | What it means | Formula (plain) | Good / Warn / Critical |
|---|---|---|---|
| **Audit Readiness Score** | Are we ready for audit | 50% coverage + 30% approval + 20% freshness | ≥80 / 55–79 / <55 |
| **Enterprise Compliance %** | Org-wide controls compliant | approved ÷ total | ≥85 / 70–84 / <70 |
| **Audit Completion %** | Audits closed on schedule | closed ÷ planned | ≥90 / 75–89 / <75 |
| **Evidence Health Score** | Evidence fresh & valid | mean record health | ≥80 / 55–79 / <55 |
| **Controls Missing Evidence** | Coverage gaps | count not-submitted | lower better |
| **Expiring Evidence** | Refresh backlog | count expiring soon | lower better |
| **Approval Success %** | Reviewer throughput health | approved ÷ submitted | ≥85 / 70–84 / <70 |
| **Rejection Rate %** | Evidence quality | rejected ÷ submitted | <10 / 10–20 / >20 |
| **Avg Validation Time** | Reviewer bottleneck | mean days to approve | <3d / 3–7d / >7d |
| **Dynamic Completeness %** | True readiness (penalized) | (ctrl·0.6+ev·0.4) − penalties | ≥80 / 65–79 / <65 |
| **Control Maturity %** | Implemented controls | implemented ÷ total | ≥80 / 55–79 / <55 |
| **Implementation Coverage** | Control rollout | implemented ÷ total | ≥80 / 55–79 / <55 |
| **Observation Closure Rate** | Catching up on findings | Σclosed ÷ Σopened | >100% = backlog ↓ |
| **Observations Net** | Backlog direction | closed − opened | negative = good |
| **Remediation SLA Compliance** | On-time fixes | on-time ÷ total | ≥85 / 70–84 / <70 |
| **Evidence Reuse %** | Collect-once-reuse-many | reused ÷ total mappings | higher better |
| **Reuse Factor** | Avg frameworks per artifact | mappings ÷ artifacts | higher better |
| **Connector Health %** | Integration trust | healthy ÷ total connectors | ≥95 / 85–94 / <85 |
| **Scheduler Success Rate** | Collection reliability | success ÷ runs | ≥98 / 90–97 / <90 |
| **BU Compliance %** | Per-business-unit posture | per-BU compliant | ≥85 / 70–84 / <70 |
| **Regional Readiness %** | Per-zone posture | per-region score | ≥85 / 70–84 / <70 |
| **AI Compliance Score** | AI governance posture | weighted 6 dimensions | ≥90 target / 75–89 / <75 |
| **Hallucination Rate %** | AI output reliability | flagged ÷ outputs | <3 / 3–8 / >8 |
| **SDLC Release Readiness** | Go-live confidence | mean of 5 stage scores | ≥85 / 70–84 / <70 |
| **ROI / Payback** | Investment value | value ÷ run cost; months to recover | higher / shorter better |

---

## Where each appears

| Dashboard | Headline KPIs |
|---|---|
| CIO | Audit Readiness, Enterprise Compliance, Audit Completion, Open VAPT |
| Enterprise | BU Compliance, BU Risk, Framework Maturity |
| Pan India | Regional Readiness, SLA Breaches, National Score |
| Trends | Implementation Coverage, Observations Net, Closure Rate, Rejection Rate |
| Evidence Health | Health Score, Missing/Expiring/Rejected |
| Evidence Approval | Approval Success, Rejection Rate, Validation Time |
| Completeness | Dynamic Completeness, Control Maturity |
| Reuse | Reuse %, Reuse Factor |
| AI Governance | AI Compliance Score, Hallucination Rate |
| AI SDLC | Stage/Release Readiness, Coverage % |
| ROI | Annual value, Hours saved, FTE, Payback, ROI % |

---

## Two rules when quoting numbers

1. **Catalog vs demo-seed:** static catalog = 15 frameworks / 305 controls / 702 evidence / 12 connectors. Demo mode seeds larger rounded numbers for presentation — say which you mean.
2. **Demo data is synthetic:** all demo KPIs are deterministic seeds, not live measurements. In real mode they derive from the Postgres evidence repository.
