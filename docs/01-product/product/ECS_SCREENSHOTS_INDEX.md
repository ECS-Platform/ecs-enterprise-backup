# ECS Screenshot Index

Part of the **ECS Product Operations Manual** (Section 8). Index of every screenshot captured from the **running ECS platform in demo mode**.

## How these were captured

- **Tool:** `demo-data/capture_product_manual.sh` (headless Google Chrome, 1600×2200 viewport).
- **Server:** ECS run locally with `DEMO_MODE=true ECS_AUTH_ENABLED=false uvicorn app.main:app` on `127.0.0.1:8000` (so every persona can reach every screen — see `docs/01-product/00-start-here/DEMO_MODE_SETUP.md`).
- **Location:** `docs/01-product/product/screenshots/`
- **Count:** **66 PNGs**, one per major screen, each named `NN-screen.png`.
- **Re-capture:** start ECS in demo mode, then run `./demo-data/capture_product_manual.sh`. To add screens, append `"NN-name::/url?role=…&user=…"` specs to the `SPECS` array in that script.

Each row maps the file to the screen, its URL, a description, and the manual sections that reference it.

| # | File | Screen | URL | Description | Referenced in |
|---|---|---|---|---|---|
| 01 | `01-login.png` | Login | `/` | Persona picker landing page | Manual §1/§8, Screen Catalog, Persona Guide |
| 02 | `02-dashboard-owner.png` | Main Dashboard (Owner) | `/dashboard?role=owner` | Owner work queue, pending/resubmit KPIs | Screen Catalog, Persona Guide §1, Journeys §4 |
| 03 | `03-dashboard-auditor.png` | Main Dashboard (Auditor) | `/dashboard?role=auditor` | Auditor review queue | Screen Catalog, Persona Guide §2, Journeys §4 |
| 04 | `04-dashboard-cio.png` | CIO Executive Dashboard | `/dashboard/cio` | Enterprise posture & analytics | Manual §8, Screen Catalog, Persona Guide §3 |
| 05 | `05-dashboard-vertical-head.png` | Vertical Head Dashboard | `/dashboard/vertical-head` | Vertical-scoped posture | Screen Catalog, Persona Guide §4 |
| 06 | `06-dashboard-compliance-head.png` | Compliance Head Dashboard | `/dashboard/compliance-head` | Framework/control oversight | Screen Catalog, Persona Guide §5/§6 |
| 07 | `07-dashboard-functional-head.png` | Functional Head Dashboard | `/dashboard/functional-head` | Function-scoped posture | Screen Catalog, Persona Guide §7 |
| 08 | `08-roi-center.png` | ROI & Value Realization | `/mvp/roi` | ROI value/hours/FTE, payback | Screen Catalog, Journeys §12, KPI A7 |
| 09 | `09-demo-overview.png` | Demo Overview | `/mvp/demo-overview` | Executive demo cockpit tiles | KPI §F, Screen Catalog |
| 10 | `10-enterprise.png` | Enterprise | `/mvp/enterprise` | BU compliance/risk bars | KPI §B, Chart guide |
| 11 | `11-pan-india.png` | Pan India | `/mvp/pan-india` | Regional readiness & SLA | KPI §B, Chart guide |
| 12 | `12-reports.png` | Reports | `/mvp/reports` | 30-pack export center | Feature Ref §8, Journeys §10 |
| 13 | `13-trends.png` | Trends | `/mvp/trends` | Historical compliance series | KPI §D, Chart guide |
| 14 | `14-framework-pci-dss.png` | Framework page (PCI DSS) | `/framework/PCI DSS` | 6 KPI tiles + tabs | Module Ref (Frameworks), KPI §G |
| 15 | `15-framework-loader.png` | Framework Loader | `/mvp/framework-loader` | Upload/activate control library | Journeys §2 |
| 16 | `16-framework-admin.png` | Framework Administration | `/mvp/framework-admin` | Onboarding wizard | Journeys §2, Persona §11 |
| 17 | `17-scheduler.png` | Scheduler | `/mvp/scheduler` | Collection job timeline | Journeys §3, Module Ref (Operations) |
| 18 | `18-predefined-queries.png` | Predefined Queries | `/mvp/predefined-queries` | Query-driven control catalog | KPI §J, Screen Catalog |
| 19 | `19-integration-health.png` | Integration Health | `/mvp/integration-health` | Connector health | Journeys §3, Feature Ref §3 |
| 20 | `20-evidence-explorer.png` | Evidence Explorer | `/mvp/evidence-explorer` | Repository evidence + correlations | Journeys §3 |
| 21 | `21-ai-ops-assistant.png` | AI Ops Assistant | `/mvp/ai-ops-assistant` | Governance copilot | Module Ref (Operations) |
| 22 | `22-bulk-upload.png` | Bulk Upload | `/mvp/upload` | Mass evidence import | Journeys §3, Persona §1 |
| 23 | `23-integrations.png` | Integrations | `/mvp/integrations` | External connectors | Feature Ref §3 |
| 24 | `24-onboarding.png` | Onboarding | `/mvp/onboarding` | Application onboarding wizard | Journeys §1 |
| 25 | `25-audit-prep.png` | Audit Prep | `/mvp/audit-prep` | Readiness cockpit + heatmap | Manual §8, Journeys §5 |
| 26 | `26-evidence-health.png` | Evidence Health | `/mvp/evidence-health` | Stale/expired/rejected scoring | KPI §C, Journeys §4 |
| 27 | `27-evidence-reuse.png` | Evidence Reuse | `/mvp/reuse` | Cross-framework reuse graph | KPI §B, Journeys |
| 28 | `28-lifecycle.png` | Lifecycle | `/mvp/lifecycle` | Evidence lifecycle states | KPI §C, Chart guide |
| 29 | `29-completeness.png` | Completeness | `/mvp/completeness` | Coverage gap analysis | KPI A2, Journeys §5 |
| 30 | `30-comparison.png` | App Comparison | `/mvp/comparison` | Application posture comparison | Chart guide, Journeys |
| 31 | `31-search.png` | Search | `/mvp/search` | Evidence discovery | Screen Catalog |
| 32 | `32-evidence-approval.png` | Evidence Approval Analytics | `/mvp/evidence-approval` | Approval efficiency/throughput | KPI §C, Journeys §4 |
| 33 | `33-platform-scorecard.png` | Role Scorecard | `/mvp/platform/scorecard` | Role-scoped governance scorecard | KPI §I |
| 34 | `34-platform-executive-summary.png` | Executive Summary | `/mvp/platform/executive-summary` | Platform executive summary | Screen Catalog |
| 35 | `35-platform-audit-readiness.png` | Audit Readiness | `/mvp/platform/audit-readiness` | Composite readiness gauge | KPI A1, Manual §5 |
| 36 | `36-platform-onboarding.png` | Application Onboarding | `/mvp/platform/onboarding` | Register an application | Journeys §1 |
| 37 | `37-platform-inventory.png` | Application Inventory | `/mvp/platform/inventory` | Onboarded application catalog | Journeys §1 |
| 38 | `38-platform-control-coverage.png` | Control Coverage | `/mvp/platform/control-coverage` | Controls with evidence / total | KPI §B |
| 39 | `39-platform-framework-coverage.png` | Framework Coverage | `/mvp/platform/framework-coverage` | Per-framework coverage | KPI §B |
| 40 | `40-platform-evidence-reuse.png` | Evidence Reuse (platform) | `/mvp/platform/evidence-reuse` | DB reuse demonstrations | KPI §B |
| 41 | `41-platform-evidence-lifecycle.png` | Evidence Lifecycle (platform) | `/mvp/platform/evidence-lifecycle` | Validate by lifecycle status | Screen Catalog |
| 42 | `42-platform-scheduler.png` | Collection Scheduler (platform) | `/mvp/platform/scheduler` | Connector schedules | Screen Catalog |
| 43 | `43-ai-assistant.png` | AI Assistant | `/mvp/ai-assistant` | Citation-grounded RAG | Feature Ref §7 |
| 44 | `44-risk-register.png` | Risk Register | `/mvp/risk-register` | Enterprise risk governance | Journeys §8, Chart guide |
| 45 | `45-exceptions.png` | Exceptions / TD | `/mvp/exceptions` | Technical-debt workflow | Journeys §7 |
| 46 | `46-exception-governance.png` | Exception Governance | `/mvp/exception-governance` | TD lifecycle & CAB queue | KPI §C, Journeys §7 |
| 47 | `47-cmdb.png` | CMDB / Assets | `/mvp/cmdb` | Asset inventory & compliance | Module Ref (Enterprise GRC) |
| 48 | `48-regulatory.png` | Regulatory Mapping | `/mvp/regulatory` | Cross-framework normalization | Chart guide |
| 49 | `49-heatmaps.png` | Executive Heatmaps | `/mvp/heatmaps` | Framework/app/BU/regional heatmaps | Chart guide, Manual §6 |
| 50 | `50-integrations-hub.png` | Integrations Hub | `/mvp/integrations-hub` | Integration orchestration | Module Ref (Enterprise GRC) |
| 51 | `51-correlation.png` | Cross-Tool Correlation | `/mvp/correlation` | Incident→control chains | Module Ref (Enterprise GRC) |
| 52 | `52-governance-analytics.png` | Governance Analytics | `/mvp/governance-analytics` | Enterprise governance intel | KPI §D, Chart guide |
| 53 | `53-ai-sdlc-home.png` | AI SDLC Home | `/mvp/ai-sdlc` | AI/SDLC governance landing | Journeys §11 |
| 54 | `54-ai-sdlc-control-tower.png` | AI SDLC Control Tower | `/mvp/ai-sdlc/control-tower` | Framework×app readiness heatmap | KPI A3, Journeys §11 |
| 55 | `55-ai-sdlc-onboarding.png` | AI SDLC Onboarding | `/mvp/ai-sdlc/onboarding` | Onboard app into AI SDLC | Journeys §11 |
| 56 | `56-ai-sdlc-requirements.png` | Requirements stage | `/mvp/ai-sdlc/requirements` | Stage worklist | Journeys §11 |
| 57 | `57-ai-sdlc-design.png` | Design stage | `/mvp/ai-sdlc/design` | Stage worklist | Journeys §11 |
| 58 | `58-ai-sdlc-development.png` | Development stage | `/mvp/ai-sdlc/development` | Stage worklist | Journeys §11 |
| 59 | `59-ai-sdlc-testing.png` | Testing stage | `/mvp/ai-sdlc/testing` | Stage worklist | Journeys §11 |
| 60 | `60-ai-sdlc-golive.png` | Go-Live stage | `/mvp/ai-sdlc/golive` | Go-Live gate | Journeys §11 |
| 61 | `61-ai-sdlc-evidence.png` | Evidence Collection (AI SDLC) | `/mvp/ai-sdlc/evidence` | Evidence status by framework | KPI §H, Journeys §11 |
| 62 | `62-ai-sdlc-findings.png` | Findings & Remediation (AI SDLC) | `/mvp/ai-sdlc/findings` | Open findings | Journeys §9/§11 |
| 63 | `63-ai-sdlc-reports.png` | AI SDLC Reports | `/mvp/ai-sdlc/reports` | 6 AI SDLC reports | Feature Ref §8C |
| 64 | `64-ai-governance-posture.png` | AI Governance Posture | `/mvp/ai-governance` | AI Compliance Score (6 dims) | Manual §8, KPI A4 |
| 65 | `65-ai-registry.png` | AI Model & Prompt Registry | `/mvp/ai-registry` | Models/prompts under governance | Module Ref (AI SDLC) |
| 66 | `66-governance-quality.png` | Governance Quality | `/mvp/governance-quality` | Governance QA scan | KPI §K |

## Pre-existing demo screenshots

The repository also contains 7 earlier screenshots under `demo-data/screenshots/` (e.g. `01-executive-summary.png`, `11-evidence-reuse.png`, `12-scorecard-cio.png`, `14-framework-coverage.png`, `15-ai-assistant-pci.png`). Those are retained for the demo narrative; the authoritative product-manual set is the 66 images above under `docs/01-product/product/screenshots/`.

## Screens not separately screenshotted

A few routes are forms, redirects, drill modals, file downloads, or path-param detail pages reached from the screens above (e.g. `/evidence/review`, `/mvp/workflow/*`, `/mvp/reports/view/{type}`, `/mvp/ai-sdlc/reports/{id}`, `/mvp/predefined-queries/detail`, `/mvp/platform/application/{slug}`). They are fully documented in `ECS_SCREEN_CATALOG.md`; capture them by adding specs to `capture_product_manual.sh` with representative path params.
