# ECS Security Reference

**Type:** Security architecture reference. **No code/UI/DB changes.** **Grounding:** `config/auth.yaml`, `config/rbac.yaml` (9 roles), `app/auth/*`, JWT/OIDC middleware, `ecs_platform/repository/schema.sql` (`audit_log`), `config/integrations.yaml` (env-resolved secrets), `config/repository.yaml` (`log_evidence_access`), `ecs_platform/rag.py` (RBAC-before-LLM). Cross-references [AI Security Architecture](../ai-sdlc/ECS_AI_SECURITY_ARCHITECTURE.md). Inferred items marked **[Inferred/Target]**.

---

## 1. Authentication
- Modes: `DEMO_MODE` (persona switch, relaxed), and `ECS_AUTH_ENABLED` JWT/OIDC for real deployments.
- JWT/OIDC middleware validates tokens; demo auth (`app/auth/demo.py`) assigns persona/role without IdP.
- **PROD:** enable auth, integrate enterprise OIDC IdP, disable demo personas.

## 2. Authorization & RBAC
- `config/rbac.yaml` defines **9 roles** (e.g., CIO, Compliance, Auditor, Application/Framework/Control/Evidence Owner, Admin, AI SDLC/Governance Owner). Legacy `role_permissions.py` coexists.
- Scope filters restrict applications/frameworks/evidence per role.
- **RBAC is applied before AI retrieval** — a restricted user with no assignments retrieves nothing (no data leak via assistant).

## 3. Encryption
- **In transit:** HTTPS to sources/providers (`verify_ssl: true`); TLS termination at edge (Nginx) in prod.
- **At rest:** PostgreSQL + MinIO storage encryption; `MINIO_SECURE=true` in prod. **[Deploy/Infra responsibility]**.
- Evidence integrity via `content_hash`; audit chain via `audit_log.prev_hash`.

## 4. Audit logging
- `audit_log(actor, role, action, resource, detail, before_state, after_state, request_id, auth_source, prev_hash)` — tamper-evident hash chain.
- `log_evidence_access: true` records evidence reads (`config/repository.yaml`).
- AI interactions logged for explainability/auditability.

## 5. Secrets
- **No secrets hardcoded** — all resolve from env at load (`${ENV}`/`${ENV:-default}`, `ecs_platform/config/loader.py`).
- **PROD:** source from a secrets manager/vault; rotate connector tokens/keys; never commit `.env`.

## 6. Certificates
- TLS certs managed at edge/infra; `verify_ssl` enforced per connector. Certificate inventory/expiry tracked as PCI evidence. **[Infra responsibility]**.

## 7. Data retention
- Evidence/audit retained per bank policy in Postgres + MinIO; backups per [Backup & Recovery](../operations/ECS_BACKUP_AND_RECOVERY_GUIDE.md). Automated retention/archival enforcement is **[Inferred/Target]**.

## 8. Evidence integrity
- Unique constraints + `content_hash` + lineage + correlation ensure provenance and dedup. Cascades preserve referential integrity.

## 9. AI security
- Anti-hallucination guardrails (`require_citations`, `refuse_without_evidence`), RBAC-before-LLM, local-first (data stays on-host with Ollama). Full detail: [AI Security Architecture](../ai-sdlc/ECS_AI_SECURITY_ARCHITECTURE.md).

## 10. Connector security
- Least-privilege service accounts, env/vault secrets, TLS, fail-fast health checks, audit-logged ingestion. See [Integrations](../developer-manual/connectors/_legacy_INTEGRATIONS_index.md).

## 11. Environment security
- Demo: relaxed auth, synthetic data, default-disabled SaaS connectors.
- UAT/PROD: auth enabled, OIDC, vaulted secrets, TLS everywhere, restricted RBAC, monitored audit log. See [Deployment](../production/ECS_DEPLOYMENT_REFERENCE.md).

## Cross-references
- AI security: [ECS_AI_SECURITY_ARCHITECTURE.md](../ai-sdlc/ECS_AI_SECURITY_ARCHITECTURE.md)
- Data model: [ECS_DATA_ARCHITECTURE_REFERENCE.md](../../02-architecture/architecture/ECS_DATA_ARCHITECTURE_REFERENCE.md)
- Deployment: [ECS_DEPLOYMENT_REFERENCE.md](../production/ECS_DEPLOYMENT_REFERENCE.md)
