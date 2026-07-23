# ECS Master Use Case Catalog

**Type:** Use case catalog (150+). **No code/UI/DB changes.** **Grounding:** ECS screens/modules/workflows/personas (see [Master Product Manual](../product/ECS_MASTER_PRODUCT_MANUAL.md), [User Journeys](../product/ECS_USER_JOURNEYS.md)). AI-specific catalog (100+) is in [docs/AI Catalog V2](../../03-development/ai-sdlc/ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md) — this master catalog spans **all** domains and cross-references it. ROI grounded in `config/roi.yaml` model (hours saved × rate; reuse multiplier); values **[Inferred/Target — validate]**.

**Row format:** *ID — Problem · Actor · Inputs→Outputs · Workflow · Business Value/ROI.*

---

## A. Audit (UC-A01..A12)
- **UC-A01** Prove audit readiness fast · Auditor · controls/evidence → readiness score · Audit Prep · avoids fire-drills; days→hours.
- **UC-A02** Assemble audit evidence pack · Auditor · framework scope → export pack · Reports · faster audit cycles.
- **UC-A03** Identify audit gaps pre-audit · Compliance · coverage → gap list · Completeness · prevents findings.
- **UC-A04** Track audit findings to closure · Auditor · observations → closure status · Risk/Exceptions · audit credibility.
- **UC-A05** Evidence freshness for audit window · Owner · ages → expiring list · Evidence Health · no stale evidence.
- **UC-A06** Per-framework audit posture · Auditor · framework → 6 KPIs · Framework page · targeted prep.
- **UC-A07** Cross-framework audit reuse · Compliance · crosswalk → reuse map · Reuse · less duplicate audit work.
- **UC-A08** Audit trail integrity · Auditor · audit_log → tamper-evident chain · — · regulator trust.
- **UC-A09** Reviewer throughput for audit SLA · Governance · reviews → approval analytics · Evidence Approval · meets deadlines.
- **UC-A10** Upcoming audit calendar · Auditor · schedule → heatmap · Audit Prep · proactive planning.
- **UC-A11** Historical audit trend · CIO · periods → trend lines · Trends · board narrative.
- **UC-A12** Drilldown finding → evidence · Auditor · finding → evidence chain · Correlation · defensible answers.

## B. Evidence (UC-E01..E12)
- **UC-E01** Centralize scattered evidence · Owner · sources → repository · Evidence Explorer · single source of truth.
- **UC-E02** Bulk import evidence · Owner · files → validated rows · Bulk Upload · mass onboarding speed.
- **UC-E03** Validate evidence sufficiency · Reviewer · evidence → sufficiency score · Evidence Review · quality gate.
- **UC-E04** Approve/reject with reason · Auditor · evidence → decision+reason · Evidence Review · consistent decisions.
- **UC-E05** Resubmit rejected evidence · Owner · feedback → new version · Lifecycle · faster remediation.
- **UC-E06** Detect expiring evidence · Governance · ages → expiry alerts · Evidence Health · continuous compliance.
- **UC-E07** Evidence lineage/provenance · Auditor · uid → lineage · — · traceability.
- **UC-E08** Reuse one artifact across frameworks · Compliance · artifact → multi-map · Reuse · collect-once savings.
- **UC-E09** Correlate evidence across tools · Admin · sources → correlation group · Correlation · stronger assurance.
- **UC-E10** Semantic evidence search · Auditor · query → ranked evidence · AI Assistant · find fast.
- **UC-E11** Faceted evidence search · Compliance · filters → results · Search · precise discovery.
- **UC-E12** Evidence health scoring · Owner · records → health score · Evidence Health · decay prevention.

## C. Frameworks (UC-F01..F12)
- **UC-F01** Onboard a new framework · FW Owner · library → controls loaded · Framework Loader/Admin · fast regulation adoption.
- **UC-F02** PCI DSS compliance posture · Compliance · evidence → PCI KPIs · Framework page · payment compliance.
- **UC-F03** DPSC self-assessment · Compliance · workbook → coverage · Framework page · RBI alignment.
- **UC-F04** OS baselining at scale · Ops · queries → pass/fail · Predefined Queries · objective hardening.
- **UC-F05** DB baselining · Ops · DB queries → results · Predefined Queries · DB assurance.
- **UC-F06** Nginx hardening · Ops · config check → results · Predefined Queries · edge security.
- **UC-F07** AppSec gates · AppSec · scans → quality gate · Framework page · secure SDLC.
- **UC-F08** VAPT remediation tracking · Risk · findings → closure · Risk Register · vuln reduction.
- **UC-F09** ITDRM resilience · Ops · backups/DR → attestation · Framework page · recoverability.
- **UC-F10** Map controls to regulations · Compliance · controls → theme crosswalk · Regulatory Mapping · coverage clarity.
- **UC-F11** Compare framework maturity · Heads · frameworks → maturity bars · Enterprise · investment focus.
- **UC-F12** Framework reuse multiplier · Compliance · crosswalk → reuse % · Reuse · cost efficiency.

## D. Controls (UC-C01..C11)
- **UC-C01** Maintain control library · FW Owner · catalog → 305 controls · Framework Admin · governance baseline.
- **UC-C02** Assign control ownership · Compliance · controls → owners · Completeness · accountability.
- **UC-C03** Assess control maturity · Compliance · evidence → maturity · Completeness · readiness clarity.
- **UC-C04** Validate control coverage · Compliance · evidence → covered % · Coverage · audit gaps.
- **UC-C05** Test control via query · Ops · query → pass/fail · Predefined Queries · objective testing.
- **UC-C06** Reuse control across frameworks · Compliance · crosswalk → shared control · Reuse · efficiency.
- **UC-C07** Raise control exception · Owner · gap → exception · Exceptions · risk-accepted transparency.
- **UC-C08** Govern exceptions/TD · Compliance · exceptions → lifecycle · Exception Governance · controlled risk.
- **UC-C09** Compensating controls · Compliance · gap → compensating + justification · Exceptions · pragmatic compliance.
- **UC-C10** Control effectiveness · Auditor · evidence+freshness → effectiveness · Evidence Health · real assurance.
- **UC-C11** Close control · Compliance · remediation → closed · Trends · backlog reduction.

## E. Risk (UC-R01..R11)
- **UC-R01** Maintain risk register · Risk · risks → register · Risk Register · governance.
- **UC-R02** Prioritize by severity · Risk · risks → severity ranking · Risk Register · focus.
- **UC-R03** Aging risk watch · Risk · dates → aging · Risk Register · no stale risk.
- **UC-R04** Incident→control correlation · Admin · incidents → chains · Correlation · root-cause assurance.
- **UC-R05** VAPT risk exposure · CIO · findings → open VAPT KPI · CIO dashboard · exec visibility.
- **UC-R06** AI risk posture · AI Gov · 6 dims → AI compliance score · AI Governance · responsible AI.
- **UC-R07** Risk heatmaps · CIO · risks → hotspots · Heatmaps · targeting.
- **UC-R08** SLA breach risk · Heads · SLA → breaches · Pan India · operational risk.
- **UC-R09** Regional risk posture · Vertical · zones → readiness · Pan India · geo risk.
- **UC-R10** Risk reporting to board · CIO · risks → exec report · Reports · governance.
- **UC-R11** Remediation tracking · Risk · plans → closure · Risk Register · risk reduction.

## F. Compliance (UC-K01..K11)
- **UC-K01** Enterprise compliance % · CIO · controls → compliance KPI · CIO · posture.
- **UC-K02** Regulatory crosswalk coverage · Compliance · controls → theme coverage · Regulatory Mapping · completeness.
- **UC-K03** Continuous compliance monitoring · Compliance · freshness → alerts · Evidence Health · always-ready.
- **UC-K04** Policy adherence (ITPP) · Compliance · policies → adherence · Framework page · governance.
- **UC-K05** ISG self-assessment · Compliance · attestations → score · Framework page · governance posture.
- **UC-K06** Compliance trend · CIO · periods → trend · Trends · trajectory.
- **UC-K07** BU compliance accountability · Heads · BUs → compliance · Enterprise · ownership.
- **UC-K08** Compliance gap remediation · Compliance · gaps → closure · Completeness · risk reduction.
- **UC-K09** Evidence-backed compliance claims · Auditor · claims → evidence · AI Assistant · defensibility.
- **UC-K10** Cross-framework compliance reuse · Compliance · crosswalk → reuse · Reuse · efficiency.
- **UC-K11** Compliance export pack · Compliance · scope → export · Reports · regulator submission.

## G. Governance (UC-G01..G11)
- **UC-G01** Governance analytics · CIO · metrics → analytics · Governance Analytics · oversight.
- **UC-G02** Governance quality QA · Admin · completeness → validation · Governance Quality · data trust.
- **UC-G03** Lifecycle completeness · Compliance · stages → maturity · Lifecycle · process health.
- **UC-G04** App comparison/benchmark · Heads · apps → benchmark · Comparison · accountability.
- **UC-G05** Exception governance/CAB · Compliance · exceptions → approvals · Exception Governance · control.
- **UC-G06** CMDB/asset governance · Admin · assets → inventory · CMDB · asset control.
- **UC-G07** Role scorecard · All · role → personalized posture · Scorecard · engagement.
- **UC-G08** Governance heatmaps · CIO · data → hotspots · Heatmaps · prioritization.
- **UC-G09** Integration governance · Admin · connectors → health · Integration Health · trust.
- **UC-G10** Evidence governance reuse · Compliance · repo → reuse · Platform Reuse · efficiency.
- **UC-G11** AI governance operating model · AI Gov · use cases → lifecycle · AI Registry · responsible AI.

## H. Executive (UC-X01..X11)
- **UC-X01** CIO single-pane posture · CIO · enterprise → KPIs · CIO dashboard · decisions.
- **UC-X02** Board-ready summary · Exec · data → exec summary · Executive Summary · governance.
- **UC-X03** Quantify ROI · CIO · model → annual value · ROI Center · investment case.
- **UC-X04** Enterprise BU view · CIO · BUs → posture · Enterprise · accountability.
- **UC-X05** Pan-India regional view · Vertical · zones → readiness · Pan India · geo oversight.
- **UC-X06** Demo overview story · Demo · platform → one-screen story · Demo Overview · stakeholder buy-in.
- **UC-X07** Executive heatmaps · MD · data → hotspots · Heatmaps · focus.
- **UC-X08** Trend narrative · CIO · periods → trends · Trends · storytelling.
- **UC-X09** Scoped head dashboards · Heads · scope → posture · Head dashboards · delegation.
- **UC-X10** Exec report exports · CIO · scope → reports · Reports · governance.
- **UC-X11** AI posture to board · CIO · AI dims → score · AI Governance · responsible AI.

## I. Operations (UC-O01..O11)
- **UC-O01** Automate evidence collection · Ops · schedules → pulls · Scheduler · efficiency.
- **UC-O02** Monitor connector health · Admin · connectors → status · Integration Health · reliability.
- **UC-O03** Query-driven controls · Ops · queries → evidence · Predefined Queries · automation.
- **UC-O04** Onboard application · Ops · app → registered · Onboarding · governance coverage.
- **UC-O05** Manage connectors · Admin · config → connectors · Integrations · integration.
- **UC-O06** Scheduler failure handling · Ops · failures → alerts · Scheduler · resilience.
- **UC-O07** Ops governance copilot · Ops · question → guidance · AI Ops Assistant · faster ops.
- **UC-O08** Evidence explorer triage · Admin · repo → browse · Evidence Explorer · investigation.
- **UC-O09** Cross-tool correlation · Admin · sources → chains · Correlation · assurance.
- **UC-O10** Integration orchestration · Admin · integrations → usage · Integrations Hub · control.
- **UC-O11** Sync run audit · Ops · runs → history · Scheduler · accountability.

## J. AI (UC-AI01..AI11) — see [AI Catalog V2](../../03-development/ai-sdlc/ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md) for 100+
- **UC-AI01** Citation-grounded Q&A · All · question → cited answer · AI Assistant · trust + speed.
- **UC-AI02** Refuse without evidence · All · question → refusal if no evidence · AI Assistant · anti-hallucination.
- **UC-AI03** Semantic evidence retrieval · Auditor · query → embeddings match · AI Assistant · discovery.
- **UC-AI04** Draft rejection reason · Reviewer · context → draft · Evidence Review · consistency.
- **UC-AI05** Auto-classify evidence · Owner · evidence → tags · Bulk Upload · efficiency [Target].
- **UC-AI06** Summarize framework posture · Compliance · framework → summary · AI Assistant · briefings.
- **UC-AI07** RBAC-scoped AI · All · role → scoped answers · AI Assistant · no data leak.
- **UC-AI08** Local-first private AI · Bank · data → on-host LLM · — · data sovereignty.
- **UC-AI09** AI-SDLC stage gating · AI SDLC · evidence → gate · Control Tower · go-live confidence.
- **UC-AI10** AI governance posture · AI Gov · dims → score · AI Governance · responsible AI.
- **UC-AI11** Hybrid cloud fallback · Bank · heavy job → cloud · — · scale [Target].

## K. Reporting (UC-RP01..RP10)
- **UC-RP01** Generate audit reports · Auditor · scope → report · Reports · audit prep.
- **UC-RP02** Export mix analytics · CIO · exports → mix · Reports · usage insight.
- **UC-RP03** AI-SDLC reports (6) · AI SDLC · data → reports · AI SDLC Reports · delivery oversight.
- **UC-RP04** Governance analytics report · CIO · metrics → report · Governance Analytics · oversight.
- **UC-RP05** Trend reports · CIO · periods → trends · Trends · narrative.
- **UC-RP06** Executive summary report · Exec · data → summary · Executive Summary · board.
- **UC-RP07** Framework compliance report · Compliance · framework → report · Framework page · regulator.
- **UC-RP08** Evidence approval report · Governance · reviews → report · Evidence Approval · SLA.
- **UC-RP09** Risk report · Risk · risks → report · Risk Register · governance.
- **UC-RP10** ROI report · CIO · model → ROI report · ROI Center · investment case.

## L. Search (UC-S01..S08)
- **UC-S01** Faceted evidence search · Compliance · filters → results · Search · discovery.
- **UC-S02** Semantic AI search · Auditor · query → ranked · AI Assistant · relevance.
- **UC-S03** Reuse-aware search · Compliance · query → reuse links · Search · efficiency.
- **UC-S04** Cross-framework search · Compliance · query → multi-fw · Search · coverage.
- **UC-S05** Owner/status search · Owner · filters → my evidence · Search · personal queue.
- **UC-S06** Control-scoped search · Compliance · control → evidence · Search · validation.
- **UC-S07** Application-scoped search · Owner · app → evidence · Search · app view.
- **UC-S08** Source-system search · Admin · source → evidence · Evidence Explorer · triage.

## M. Integrations (UC-I01..I10)
- **UC-I01** Jira delivery evidence · Ops · Jira → evidence · Integrations · SDLC assurance.
- **UC-I02** Confluence policy evidence · Compliance · Confluence → policies · Integrations · governance.
- **UC-I03** ServiceNow change/CAB · Compliance · SNOW → change evidence · Integrations · change control.
- **UC-I04** Prisma cloud findings · Risk · Prisma → findings · Integrations · cloud security.
- **UC-I05** SharePoint evidence files · Owner · SP → files · Integrations · doc evidence.
- **UC-I06** Teams approval evidence · Governance · Teams → approvals · Integrations · decision trail.
- **UC-I07** Azure DevOps SDLC · AppSec · AZDO → PR/pipeline · Integrations · secure SDLC.
- **UC-I08** GitHub SCM evidence · AppSec · GitHub → PR/branch · Integrations · secure SDLC.
- **UC-I09** Jenkins build/test · AppSec · Jenkins → builds · Integrations · CI/CD assurance.
- **UC-I10** Tenant onboarding (no code) · Admin · env vars → enabled connector · Integrations · fast onboarding.

## N. Workflow (UC-W01..W10)
- **UC-W01** Application onboarding workflow · Ops · app → governed app · Onboarding · coverage. (see [guide](../../03-development/operations/ECS_APPLICATION_ONBOARDING_GUIDE.md))
- **UC-W02** Framework onboarding workflow · FW Owner · framework → active · Framework Admin · adoption.
- **UC-W03** Evidence collection workflow · Ops · schedule → evidence · Scheduler · automation.
- **UC-W04** Evidence approval workflow · Auditor · evidence → approved · Evidence Review · quality.
- **UC-W05** Audit preparation workflow · Auditor · scope → ready · Audit Prep · readiness.
- **UC-W06** Control validation workflow · Compliance · evidence → covered · Coverage · assurance.
- **UC-W07** Exception handling workflow · Compliance · gap → governed exception · Exception Governance · control.
- **UC-W08** Risk management workflow · Risk · risk → mitigated · Risk Register · governance.
- **UC-W09** Report generation workflow · Auditor · scope → report · Reports · output.
- **UC-W10** AI-SDLC review workflow · AI SDLC · stages → go-live · Control Tower · delivery.

---

## ROI model note
Per `config/roi.yaml` (`roi/workbook.py`): value = hours-saved × rate + reuse savings; surfaced on [ROI Center](../product/ECS_MASTER_PRODUCT_MANUAL.md). **A documented rate-basis discrepancy exists** (`cost_per_hour: 1500` vs ₹1,000/hr tables) — see [documentation audit](../../executive/documentation_audit.md); quote with that caveat. Per-use-case ROI figures are **[Inferred/Target — validate]**.

## Cross-references
- Screens: [ECS_MASTER_PRODUCT_MANUAL.md](../product/ECS_MASTER_PRODUCT_MANUAL.md) · KPIs: [ECS_MASTER_KPI_DICTIONARY.md](../product/ECS_MASTER_KPI_DICTIONARY.md) · AI use cases: [Catalog V2](../../03-development/ai-sdlc/ECS_LOCAL_LLM_USE_CASE_CATALOG_V2.md) · Journeys: [User Journeys](../product/ECS_USER_JOURNEYS.md)
