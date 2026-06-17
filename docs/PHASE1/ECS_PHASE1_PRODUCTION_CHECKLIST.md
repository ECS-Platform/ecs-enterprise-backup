# ECS Phase 1 — Production Readiness Checklist

**Type:** Documentation only. No code modified.
**Date:** 2026-06-17
**Companion:** `ECS_PHASE1_IMPLEMENTATION_BACKLOG.md`, `ECS_PHASE1_GAP_ANALYSIS.md`,
`ECS_PHASE1_UAT_CHECKLIST.md`.

**Entry condition:** UAT checklist complete and UAT business sign-off obtained.
Production introduces additional **security, durability, and operability** gates
beyond UAT.

---

## A. Configuration (`config/environments/prod.yaml`)

- [ ] **B02** App hosts/`base_url`, `databases.*`, `connectors.*` set to real production endpoints.
- [ ] **B04** `predefined_query_targets.*` replaced with the **production** inventory (no `172.16.x` placeholders).
- [ ] **B03** Live predefined-query connector targets set to production systems.
- [ ] `environment: prod`, `tenant`, `region` correct.
- [ ] `authentication.sso.enabled: true` (shipped default) with real provider.
- [ ] `storage.object_store.secure: true` (shipped default) with real endpoint.
- [ ] **B20** `prod.yaml` peer-reviewed and approved (change management).

## B. Secrets & identity

- [ ] **B07** All `*_env` secrets sourced from vault / K8s Secret — none on disk or in YAML.
- [ ] **B10** SSO/IdP (SAML/OIDC) provisioned: metadata URL + `ECS_SSO_CLIENT_ID`/`ECS_SSO_CLIENT_SECRET`.
- [ ] **B24** Secrets rotation policy defined (automation may be Phase 3).

## C. Data stores

- [ ] **B08** Production evidence-repository PostgreSQL provisioned (HA), schema initialised.
- [ ] **B09** Production object store with TLS + scoped credentials.
- [ ] **B18** Backup + DR configured and **restore-tested** for repository + object store.
- [ ] **B16** Production LLM (Ollama) + pgvector provisioned; RAG index warmed on production evidence (if AI in scope).

## D. Security & network

- [ ] **B19** TLS certificates provisioned for ECS + connector/application endpoints; `verify_ssl: true` honoured.
- [ ] Network policy / egress rules allow only required connector/app/db endpoints.
- [ ] Least-privilege service accounts for connectors and DBs.
- [ ] **B11** DB drivers present in the hardened production image.

## E. Validation & startup gates

- [ ] **B12** `ECS_ENV=prod python -m config.config_validation` → **PASS** in the deploy pipeline; **deploy fails on non-zero exit**.
- [ ] `ECS_VALIDATE_CONFIG` not set to `off` (strict-env hard-fail remains active).
- [ ] Startup logs confirm `Active environment: prod`, repository + governance schema ready, 0 validation errors.

## F. Operability

- [ ] **B17** Monitoring/alerting live: connector sync health, evidence repo, object store, RAG, env-validation gate.
- [ ] Centralised logging + audit trail shipping.
- [ ] Health/readiness endpoints wired to the orchestrator.
- [ ] **B21** Production deployment runbook + secrets matrix published; rollback to prior config documented (`ECS_ENV` repoint / config revert).

## G. Functional verification (production-safe)

- [ ] Per-persona page crawl returns HTTP 200/303 (no 5xx, no forbidden body strings).
- [ ] Integration Health: production connectors authenticate; "Sync All" degrades gracefully on any single failure (no page crash).
- [ ] Evidence read/write against the production repository verified.
- [ ] A production report pack exports successfully.

## H. Production GO / NO-GO

- [ ] All P1 items (B01–B10 as applicable, B07, B08, B09, B10, B12, B17, B18) ✅.
- [ ] **B15** load/perf result accepted for production concurrency.
- [ ] Change Advisory Board approval (**B20**).
- [ ] Rollback plan rehearsed.

---

### Production GO criteria
A–G complete with E/F green and H approved. Deferred to **Phase 2** (do not block
Phase 1 PROD for the Postgres/Linux/SonarQube estate): **B22** Oracle/MySQL/SQL
Server live connectors, **B23** Windows live connector. Deferred to **Phase 3**:
**B24** secrets-rotation automation.
