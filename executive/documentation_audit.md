# ECS — Documentation Consistency Audit

**Reviewers:** Principal Enterprise Architect · Principal Technical Editor · Principal Banking Governance Consultant
**Scope:** The 11 executive deliverables generated in `/executive`, `/product`, `/strategy`, `/presales`, `/ux`, `/governance`.
**Method:** Cross-document consistency review plus verification of every quantitative and architectural claim against the live implementation (`modules/`, `ecs_platform/`, `config/`, `tests/`). Counts were computed directly from code, not from prior documents.

**Verification commands of record (re-runnable):**
- Framework / control / evidence counts: `catalog_stats()` on `modules/frameworks/engines/framework_catalog.py` → `{framework_count: 15, control_count: 305, evidence_count: 702}`.
- Connector count: `ls ecs_platform/connectors/*_connector.py` → **12**; `config/integrations.yaml` integration keys → **12**.
- Report packs: `_REPORT_DEFS` in `modules/executive_overview/engines/reporting_module.py` → **30**.
- Control themes: `CONTROL_THEMES` in `framework_intelligence.py` → **18**.
- Tests: `ls tests/*.py` → **38**. Docker services in `docker-compose.yml` → **10**. RBAC roles in `config/rbac.yaml` `rbac_catalog.roles` → **9**.

---

## 1. Audit Summary

| # | Issue | Category | Severity | Auto-corrected? |
|--:|---|---|:--:|:--:|
| A1 | Framework count stated as **16**; actual static catalog is **15** | Architecture not supported by implementation | **High** | ✅ Yes |
| A2 | Connector count stated as **13**; actual is **12** (also contradicts own 12-item enumerations) | Unsupported metric / internal contradiction | **High** | ✅ Yes |
| A3 | "Interface-complete SaaS connectors" stated as **10**; actual is **9** (12 − 3 live) | Unsupported metric | **High** | ✅ Yes |
| A4 | Controls/evidence stated as **~307 / ~706**; actual is **305 / 702** | Unsupported metric | **Medium** | ✅ Yes |
| A5 | ROI blended rate inconsistency: `config/roi.yaml` = **₹1,500/hr**, but headline tables (₹4.54 Cr) computed at **₹1,000/hr** | Contradiction between documents | **Medium-High** | ⚠️ Partial (clarifying note added; headline ₹ values left for finance sign-off) |
| A6 | Two coexisting ROI documents with different rate bases (`executive/ecs_roi_model.md` pre-existing vs `strategy/ecs_roi_model.md`) | Duplicate / potential confusion | **Low** | ⚠️ Partial (pointer note added; consolidation left for human) |
| A7 | ROI workstream costs (~₹7.2 Cr/yr) presented alongside payback run cost (₹2 Cr/yr) without reconciliation | Potential confusion | **Low** | ✅ Yes (clarifying note) |
| A8 | Cross-document recommendations repeated across board/strategy/readiness/backlog | Duplicate recommendations (benign) | **Info** | N/A (intentional alignment; see §8) |

**Net result:** No invented capabilities, no broken file references, and no contradictory recommendations were found. All defects are quantitative/precision issues; the four clear factual errors (A1–A4) are auto-corrected, and the two ROI-basis items (A5–A6) are annotated with the financially-sensitive number changes deferred to human sign-off.

---

## 2. Issue A1 — Framework count (16 → 15) · **High**

**Finding.** Multiple documents state "16 frameworks." The static `FRAMEWORK_CATALOG` contains exactly **15** keys: PCI DSS, DPSC, OS Baselining, DB Baselining, Nginx Baselining, AppSec, VAPT, CSITE, ITPP, ITDRM, SOC2, ISO27001, RBI Cyber Security, ISG, ASST. `catalog_stats()` returns `framework_count: 15`. (The "16" likely originated from `docs/developer-manual/ECS_MODULE_OWNERSHIP.md`, which states a *target* acceptance criterion, and from runtime growth via `get_merged_framework_catalog()`, which adds dynamically onboarded frameworks.)

**Locations.**
- `executive/ecs_board_summary.md` (§1 narrative; §3 capability table)
- `product/ecs_product_assessment.md` (module table; §2.1; §3 scorecard)
- `strategy/ecs_competitive_analysis.md` (§2 differentiator #2)
- `presales/ecs_customer_pitch.md` (§3.4; §4 fit table)

**Recommended correction.** Replace "16 frameworks/catalogs" with "15", optionally noting that the platform can onboard additional frameworks at runtime (Framework Loader / dynamic catalog), so the *live* count may exceed 15. **Applied.**

---

## 3. Issue A2 — Connector count (13 → 12) · **High**

**Finding.** Documents claim "13 connectors" in `ecs_platform/connectors/`. There are exactly **12** connector implementations (azure_devops, confluence, figma, gitea, github, jenkins, jira, prisma, servicenow, sharepoint, sonarqube, teams), and `config/integrations.yaml` defines exactly **12** integrations. The error is also *internally contradictory*: the same documents enumerate 12 connector names while asserting "13."

> Note: the operations module additionally provides scanning/infra connectors (gitleaks, linux, postgresql, sonarqube, trivy). These are a separate connector family and were never the basis of the "13" claim; the enterprise-source connector count is 12.

**Locations.**
- `executive/ecs_board_summary.md` (§3 capability table)
- `executive/ecs_master_index.md` (§2 facts table)
- `executive/ecs_executive_demo_story.md` (Act 3)
- `product/ecs_product_assessment.md` (module table; §3 scorecard)
- `governance/ecs_production_readiness.md` (§2.4 connector framework row)
- `presales/ecs_customer_pitch.md` (§3.1)

**Recommended correction.** Replace "13 connectors" with "12 connectors." **Applied.**

---

## 4. Issue A3 — Interface-complete SaaS count (10 → 9) · **High**

**Finding.** With 12 total connectors and 3 live in development (Gitea, Jenkins, SonarQube), the remaining interface-complete connectors number **9** (Jira, GitHub, Confluence, Figma, ServiceNow, Teams, SharePoint, Prisma Cloud, Azure DevOps), not 10. (Derivative of A2.)

**Locations.**
- `executive/ecs_master_index.md` (§2 facts table: "10 interface-complete")
- `product/ecs_product_assessment.md` (§2.5 heading; §6 recommendation: "10 SaaS connectors await")
- `strategy/ecs_competitive_analysis.md` (§3 disadvantages table)

**Recommended correction.** Replace "10 interface-complete / 10 SaaS" with "9." **Applied.**

---

## 5. Issue A4 — Controls/evidence (~307 / ~706 → 305 / 702) · **Medium**

**Finding.** Documents cite "~307 controls / ~706 evidence" (carried from the older `ECS_ARCHITECTURE_BASELINE.md`). The current catalog returns **305 controls / 702 evidence** (`catalog_stats()`). The figures are close, and the tilde signalled approximation, but the audit requires exact, source-verifiable numbers.

**Locations.**
- `executive/ecs_board_summary.md` (§1; §3 table)
- `executive/ecs_master_index.md` (§2 facts table)
- `product/ecs_product_assessment.md` (§2.1)

**Recommended correction.** Replace "~307 controls / ~706 evidence" with "305 controls / 702 evidence." **Applied.**

---

## 6. Issue A5 — ROI blended hour-rate basis · **Medium-High**

**Finding.** `config/roi.yaml` sets `cost_per_hour: 1500`. However, the headline ROI tables (25-app: 45,438 hours → ₹4.54 Cr Expected) are arithmetically consistent only with **₹1,000/hr** (45,438 × ₹1,000 = ₹4.54 Cr; at ₹1,500/hr the figure would be ~₹6.82 Cr). These tables derive from the pre-existing ROI workbook (`executive/ecs_roi_model.md`), which explicitly states "cost-per-hour ₹1,000." The generated documents present the ₹1,500 config assumption and the ₹1,000-based headline figures together, which is contradictory.

**Locations.**
- `strategy/ecs_roi_model.md` (§1.1 assumptions lists ₹1,500; §4 headline tables use ₹1,000 basis)
- `executive/ecs_board_summary.md` (§5 intro states "blended ₹1,500/hr" above the ₹4.54 Cr table)

**Recommended correction.**
- **Low-risk (applied):** Add an explicit basis note in both documents distinguishing the **config engine default (₹1,500/hr)** from the **published workbook headline tables (₹1,000/hr)**, and state that at ₹1,500/hr the 25-app Expected saving scales to ~₹6.82 Cr.
- **Deferred to human / finance sign-off (NOT auto-applied):** choosing a single canonical rate and recomputing all headline ₹ values. Silently rewriting board-facing financial figures is not a low-risk edit; finance should ratify the rate before the tables are restated.

---

## 7. Issue A6 — Duplicate ROI documents · **Low**

**Finding.** Two ROI artifacts now coexist: the pre-existing `executive/ecs_roi_model.md` (₹1,000/hr workbook basis) and the generated `strategy/ecs_roi_model.md` (cites `config/roi.yaml`). All cross-references in the new package point to `strategy/ecs_roi_model.md`, but two ROI documents with different rate bases can confuse readers.

**Recommended correction.**
- **Low-risk (applied):** Add a pointer note in `strategy/ecs_roi_model.md` acknowledging the pre-existing workbook doc and clarifying which is canonical for this package.
- **Deferred to human:** consolidating or retiring one document (the pre-existing file is outside the "generated documents" scope and should not be unilaterally removed).

---

## 8. Issue A7 — ROI workstream vs run-cost reconciliation · **Low**

**Finding.** `strategy/ecs_3_year_strategy.md` (§6) lists seven workstreams summing to ~₹7.2 Cr/yr, while the payback model uses `annual_run_cost: ₹2 Cr/yr`. Both originate from `config/roi.yaml`, which labels the workstreams "illustrative & configurable." Presenting both without a note can read as a contradiction.

**Recommended correction (applied).** Add a one-line note that the workstream totals are an *illustrative team-investment view*, distinct from the ROI denominator (`annual_run_cost`), per the config's own annotation.

---

## 9. Issue A8 — Repeated recommendations (benign) · **Informational**

**Finding.** The recommendations to (a) enable SSO/IdP and enforce RBAC, (b) converge persistence onto a single system of record, (c) complete a security review, (d) stand up HA/DR/observability, and (e) onboard enterprise connectors recur across the board summary, product assessment, 3-year strategy, production readiness and backlog. This is **intentional alignment, not contradiction** — every instance is consistent, and `product/ecs_enterprise_backlog.md` is the single canonical, sized source that the others reference.

**Recommended action.** None required. The audit confirms the recurring recommendations are mutually consistent and traceable to one backlog. No conflicting guidance was found.

---

## 10. Checks That Passed (no issues found)

| Check | Result |
|---|---|
| Invented capabilities | None. Every capability traces to code/config or `demo-data/ECS_DEMO_NARRATIVE.md` (connectors, crosswalk reuse, grounded RAG, sufficiency engine, RBAC, AI-SDLC, reports). |
| Broken file references | None. All cited paths resolve: `app/sufficiency/`, `app/audit/`, `app/auth/authz.py`, `modules/shared/static/js/drilldown_engine.js`, `modules/shared/drilldowns/ecs_universal_drill_engine.py`, `modules/shared/services/persona_display.py`, `audit_schedule_engine.py`, `framework_intelligence.py`. All cross-document links resolve. |
| Application counts | Consistent: 20 (showcase) / 10 onboarded (live flow) across all docs. |
| Reuse metrics | Consistent: 5.0×, 48 evidence → 240 obligations → 192 saved (matches `demo-data/ECS_DEMO_NARRATIVE.md`). |
| Readiness formula | Consistent: 50% control coverage + 30% approved evidence + 20% freshness. |
| Report packs (30) | Verified accurate (`_REPORT_DEFS` len = 30). |
| Control themes (18) | Verified accurate (`CONTROL_THEMES` len = 18). |
| Test suites (38) | Verified accurate. |
| Docker services (10) | Verified accurate. |
| RBAC roles (9) / personas (7) | Verified accurate (`rbac_catalog.roles` = 9). |
| Sufficiency weights / bands | Verified accurate against `config/sufficiency.yaml`. |
| LLM/vector providers | Verified accurate against `config/llm.yaml`, `config/vectorstore.yaml`. |

---

## 11. Correction Log (this audit cycle)

**Auto-corrected (low-risk, applied in a separate commit):**
- A1: "16 frameworks" → "15 frameworks" (with dynamic-onboarding note where appropriate).
- A2: "13 connectors" → "12 connectors."
- A3: "10 interface-complete / SaaS" → "9."
- A4: "~307 / ~706" → "305 / 702."
- A5 (note only): ROI rate-basis clarification added to `strategy/ecs_roi_model.md` and `executive/ecs_board_summary.md`.
- A6 (note only): canonical-ROI pointer added to `strategy/ecs_roi_model.md`.
- A7 (note only): workstream-vs-run-cost clarification added to `strategy/ecs_3_year_strategy.md`.

**Deferred to human review (financially or scope sensitive):**
- A5: restating headline ROI ₹ values to a single ratified hour-rate.
- A6: consolidating/retiring the pre-existing `executive/ecs_roi_model.md`.

**Canonical metrics source going forward:** the `executive/ecs_master_index.md` "ECS at a Glance" table is designated the single source of truth for platform counts; all other documents should defer to it.
