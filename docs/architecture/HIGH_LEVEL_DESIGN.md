# ECS High-Level Design (C4)

C4-model view of ECS (Context → Container → Component). This complements the
existing Mermaid HLD, which covers business capabilities, data/integration/
security/deployment layers in depth.

> **Reuse note.** The detailed, non-C4 HLD already exists —
> [`ecs_hld.md`](ecs_hld.md) (8 Mermaid sections). This document adds the **C4
> diagrams** (the one thing missing from the architecture set) and links out for
> everything else. Deeper views: [`ecs_lld.md`](ecs_lld.md) (LLD),
> [`ENTERPRISE_ARCHITECTURE.md`](ENTERPRISE_ARCHITECTURE.md) (bank/GCP topology),
> [`ECS_SEQUENCE_DIAGRAMS.md`](ECS_SEQUENCE_DIAGRAMS.md) (flows).

---

## C4 Level 1 — System Context

```mermaid
C4Context
  title ECS — System Context
  Person(owner, "Application Owner", "Uploads/owns evidence")
  Person(auditor, "Auditor", "Reviews evidence, runs audit queries")
  Person(exec, "CISO / CIO", "Consumes readiness dashboards")
  System(ecs, "ECS", "Enterprise Evidence Collection System")
  System_Ext(idp, "Bank IdP", "SSO / OIDC")
  System_Ext(saas, "SaaS / DevSecOps", "Jira, Confluence, ServiceNow, SonarQube, GitHub, Jenkins, Azure DevOps, ...")
  System_Ext(cloud, "Cloud posture", "AWS / Azure / GCP")
  System_Ext(targets, "Internal DBs & hosts", "via jump server")
  System_Ext(llm, "LLM runtime", "Ollama / Gemini")
  Rel(owner, ecs, "Uses", "HTTPS")
  Rel(auditor, ecs, "Uses", "HTTPS")
  Rel(exec, ecs, "Views", "HTTPS")
  Rel(ecs, idp, "Authenticates via", "OIDC/JWT")
  Rel(ecs, saas, "Collects evidence", "REST")
  Rel(ecs, cloud, "Collects posture", "REST/API")
  Rel(ecs, targets, "Collects via jump server", "DB/SSH")
  Rel(ecs, llm, "Grounded Q&A", "HTTP")
```

---

## C4 Level 2 — Containers

```mermaid
C4Container
  title ECS — Containers
  Person(user, "Bank user")
  System_Boundary(ecs, "ECS") {
    Container(web, "Web/API app", "FastAPI + Jinja2", "UI + REST; auth/RBAC; engines")
    Container(rag, "LLM-RAG service", "Python", "Retrieval + generation, grounding, citations")
    ContainerDb(repo, "Evidence Repository", "PostgreSQL", "Evidence, controls, frameworks, audit log")
    ContainerDb(vec, "Vector store", "pgvector", "Embeddings for RAG")
    ContainerDb(cache, "Cache/state", "Redis", "Sessions/state/cache")
    Container(obj, "Object store", "GCS / MinIO", "Evidence artifacts")
  }
  System_Ext(agent, "DB Agent", "Jump-server micro-service")
  Rel(user, web, "HTTPS")
  Rel(web, rag, "Query")
  Rel(web, repo, "Read/write")
  Rel(web, vec, "Search")
  Rel(web, cache, "Read/write")
  Rel(web, obj, "Store/fetch")
  Rel(agent, web, "Uploads evidence", "HTTPS")
```

---

## C4 Level 3 — Components (Web/API app)

```mermaid
C4Component
  title ECS Web/API app — Components
  Container_Boundary(app, "Web/API app") {
    Component(routes, "Route registrars", "FastAPI routers", "UI + /api/* endpoints")
    Component(auth, "Auth & RBAC", "app/auth/*", "OIDC/JWT, RBAC, guards, security mode")
    Component(evidence, "Evidence engines", "modules/*/engines", "Repository, upload, validation, reuse, lifecycle")
    Component(audit, "Audit intelligence", "modules/audit_intelligence", "Readiness, observations, prompt workbench, executor")
    Component(connectors, "Connector framework", "modules/operations/integrations", "Adapters + workbench + executor")
    Component(scheduler, "Scheduler", "asset_scheduler + scheduler_execution", "Plan/queue/execute jobs")
    Component(llmc, "LLM/RAG client", "ecs_platform/rag + llm_engine", "Provider abstraction, retrieval")
  }
  Rel(routes, auth, "Enforces")
  Rel(routes, evidence, "Invokes")
  Rel(routes, audit, "Invokes")
  Rel(audit, connectors, "Collects via")
  Rel(scheduler, connectors, "Executes")
  Rel(audit, llmc, "Grounded answers")
```

> If your Mermaid renderer does not support the `C4*` shorthand, the same
> structure is expressed as standard flowcharts in [`ecs_hld.md`](ecs_hld.md).

---

## Related
- [`ecs_hld.md`](ecs_hld.md) · [`LOW_LEVEL_DESIGN.md`](LOW_LEVEL_DESIGN.md) · [`SOLUTION_ARCHITECTURE.md`](SOLUTION_ARCHITECTURE.md) · [`ENTERPRISE_ARCHITECTURE.md`](ENTERPRISE_ARCHITECTURE.md) · [`ARCHITECTURE_INDEX.md`](ARCHITECTURE_INDEX.md)
