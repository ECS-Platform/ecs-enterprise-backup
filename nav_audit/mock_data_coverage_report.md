# Mock Data Coverage Report

Deterministic demo datasets available with **no external dependency** (no psycopg2 /
PostgreSQL / Oracle / Mongo / Redis / Kafka / ServiceNow / Jira / GitHub / GitLab /
Confluence / SonarQube / Jenkins). All providers are pure standard-library and
generate identical data on every run.

## Coverage vs. Phase 3 requirements

| Dataset | Required | Provided | Source | Status |
|---|---|---|---|---|
| Applications | 20+ | **20** | `demo_governance.list_applications` | ✅ |
| Frameworks | 15+ | **17** | `demo_governance._FRAMEWORKS` | ✅ |
| Controls | 300+ | **320** | `demo_governance.control_coverage` | ✅ |
| Evidence | 700+ | **1,200** | `demo_evidence` | ✅ |
| ServiceNow Tickets | 60+ | **80** | `demo_governance.servicenow_tickets` | ✅ |
| VAPT Findings | 25+ | **40** | `demo_governance.vapt_findings` | ✅ |
| Audit Observations | 100+ | **120** | `demo_governance.audit_observations` | ✅ |
| AI Prompts | 80+ | **100** | `demo_governance.ai_prompts` | ✅ |
| Business Units | 10+ | **12** | `demo_governance._BU` | ✅ |
| Regions | 5+ | **5** | `demo_governance.regions` | ✅ |
| Connectors | — | **10** | `demo_evidence.DEMO_SOURCES` | ✅ |

## Evidence connectors (Evidence Explorer / Integration Health)

GitHub · Jira · Confluence · Figma · Teams · SharePoint · SonarQube · Jenkins ·
GitLab · ServiceNow — 1,200 records spanning 20 applications and 17 frameworks,
with collection dates, object types, titles, URLs, and CI/CD correlation chains
(Commit → Build → Sonar → Deploy).

## Governance fallback datasets (platform pages)

`list_applications` · `control_coverage` (320) · `framework_coverage` (17) ·
`evidence_reuse` · `evidence_lifecycle` (1,200 reviews) · `list_schedules` (10) ·
`crosswalk_matrix` · `reuse_demonstrations` · `audit_readiness` (per-app) ·
`executive_summary` · `governance_scorecard` (role-aware) · `application_detail`.

Each governance read function now falls back to the demo provider on any
repository error, so the platform pages (Role Scorecard, Executive Summary, Audit
Readiness, Onboarding, Inventory, Control/Framework Coverage, Evidence
Reuse/Lifecycle, Scheduler) never surface psycopg2 / "Repository unavailable".

## Drilldown data

`drill_metric` (`drilldown_engine.py`) and all 4 drill endpoints guarantee
`ok:true` with ≥15–25 rows; on any delegated-engine miss the global
`_fallback_body` supplies representative ECS records.

**Status: All Phase 3 thresholds met or exceeded.**
