# ECS Documentation Package — Index

This package documents the **actual implemented architecture** of the ECS (Evidence & Compliance
System) platform, derived strictly from the repository at `/Users/nikhil/Documents/ECS`. All
capability claims are cited to source files. Forward-looking content is tagged **[ASSUMPTION]**,
**[RECOMMENDATION]**, or **[ROADMAP]**.

---

## Artifacts

| # | Document | Path | Contents |
|---|---|---|---|
| 1 | **Enterprise Architecture Review** | [architecture/ecs_enterprise_architecture_review.md](architecture/ecs_enterprise_architecture_review.md) | Current-state architecture, module decomposition, domain model, strengths, risks, technical debt, scalability, security, banking-regulatory readiness |
| 2 | **High-Level Design (HLD)** | [hld/ecs_hld.md](hld/ecs_hld.md) | Business, application, data, integration, security, deployment, persona, and governance architecture |
| 3 | **Low-Level Design (LLD)** | [lld/ecs_lld.md](lld/ecs_lld.md) | Per-module components, controllers, services, models, APIs, UI flows, validation, dependencies |
| 4 | **ER Diagram Package** | [diagrams/ecs_er_diagrams.md](diagrams/ecs_er_diagrams.md) | Mermaid ER diagrams: users, roles, applications, frameworks, controls, findings, evidence, audits, observations, AI-SDLC, reports |
| 5 | **System Sequence Diagrams** | [diagrams/ecs_sequence_diagrams.md](diagrams/ecs_sequence_diagrams.md) | Mermaid sequence diagrams: login, evidence submission, audit lifecycle, AI-SDLC assessment, framework assessment, drilldown, dashboard analytics, report generation |
| 6 | **Deployment Architecture** | [architecture/ecs_deployment_architecture.md](architecture/ecs_deployment_architecture.md) | Current deployment, container, runtime, network; future cloud, HA, DR architecture |
| 7 | **Executive Technology Dossier** | [executive/ecs_technology_dossier.md](executive/ecs_technology_dossier.md) | Platform overview, strategic positioning, differentiation, governance & AI-governance capabilities, risk reduction, roadmap |
| 8 | **Operations Runbook** | [operations/ecs_runbook.md](operations/ecs_runbook.md) | Startup, shutdown, backup, recovery, incident management, monitoring, troubleshooting |

---

## How to read this package

- **Executives / leadership:** start with #7 (Dossier), then #1 (Architecture Review).
- **Architects:** #1 → #2 (HLD) → #6 (Deployment).
- **Engineers:** #3 (LLD) → #4 (ER) → #5 (Sequences).
- **Operations / SRE:** #8 (Runbook) → #6 (Deployment).

## Source-of-truth anchors (key files)

- Entry point & routing: `app/main.py`
- Cross-cutting state & workflow: `modules/shared/services/ecs_state.py`,
  `modules/shared/services/evidence_workflow_engine.py`
- Universal drilldown: `modules/shared/services/drilldown_engine.py`,
  `modules/shared/drilldowns/ecs_universal_drill_engine.py`
- Framework catalog: `modules/frameworks/engines/framework_catalog.py`
- AI-SDLC: `modules/ai_sdlc/engines/ai_sdlc_workflow_engine.py`
- Auth & RBAC: `app/auth/`, `config/auth.yaml`, `config/rbac.yaml`
- Deployment: `Dockerfile`, `docker-compose.yml`

## Conventions

- **[ASSUMPTION]** — inferred, not directly stated in code.
- **[RECOMMENDATION]** — proposed target state, not currently implemented.
- **[ROADMAP]** — forward-looking capability for a future phase.
- Mermaid diagrams render in GitHub and most Markdown viewers.
