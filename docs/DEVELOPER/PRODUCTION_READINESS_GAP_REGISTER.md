# ECS Production Readiness Gap Register

**Purpose.** A transparent, professional register of what remains between the
current, fully-validated ECS build and a hardened production deployment in the
bank. This is **not** a defect list — the platform is complete and green offline
end-to-end. These are the **operational and environment** items that are, by
design, decided and provisioned at deployment time (credentials, infrastructure,
data policy), not baked into product code.

> Cross-refs: [PRODUCTION_HARDENING_GUIDE.md](PRODUCTION_HARDENING_GUIDE.md),
> [AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md](AUDIT_INTELLIGENCE_PERSISTENCE_GUIDE.md),
> [UAT_INTEGRATION_GUIDE.md](UAT_INTEGRATION_GUIDE.md).

**Legend — Status:** ✅ Done · 🟡 Foundation in place (opt-in / config) · ⛳ Pending (deployment-time).

---

## Summary

| # | Area | Status | Owner (typical) |
|---|------|--------|-----------------|
| 1 | In-memory stores vs Postgres persistence | 🟡 Foundation in place | Platform Eng |
| 2 | Real connector credentials | ⛳ Pending | Security / Platform |
| 3 | Live UAT validation | ⛳ Pending | App teams / Audit |
| 4 | External API pagination / rate limits | 🟡 Foundation in place | Platform Eng |
| 5 | Kubernetes / OpenShift config | ⛳ Pending | Infra / SRE |
| 6 | Azure AD / OIDC production mapping | ⛳ Pending | IAM |
| 7 | Secrets manager | ⛳ Pending | Security |
| 8 | Monitoring / alerting | ⛳ Pending | SRE |
| 9 | HA / deployment | ⛳ Pending | SRE / Platform |
| 10 | Performance / load testing | 🟡 Safeguards in place | Platform Eng / QA |
| 11 | Data retention & audit-log policy | ⛳ Pending (policy) | Audit / Data Gov |

---

## 1. In-memory stores vs future Postgres persistence — 🟡

**Now.** Audit-intelligence working state (runs, results, validation, observations,
evidence versions, packs, scheduler history) lives in fast in-memory engine
stores. A **DB-ready persistence foundation** ships alongside them: an abstract
`AuditPersistence` interface, an in-memory reference implementation, and a SQL
skeleton (SQLite default, **Postgres-ready**) with an idempotent schema
(`docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql`). Tests cover both backends with no live
DB. See the persistence guide.

**Gap.** Engines are not yet auto-wired to the durable store (adoption is opt-in),
and Postgres itself must be provisioned. **To close:** provision Postgres, apply
the schema, `set_persistence(SqlAuditPersistence(...))` at startup behind a flag,
and wire the engine write-paths (documented in the persistence guide §6).

## 2. Real connector credentials required — ⛳

**Now.** All connectors and 11 enterprise integrations are config-driven skeletons;
with no credentials they degrade cleanly to `not_configured` and make **no live
calls**. **Gap.** Real read-only service-account credentials must be provisioned
per target and supplied via env / secret manager (never Git). **To close:**
create least-privilege accounts; populate `.env.uat` / secret store; verify with
`config_status()` / `/api/audit/integrations/health`.

## 3. Live UAT validation pending — ⛳

**Now.** Everything is validated **offline** (mocked transports, in-memory state,
161+ scoped tests + demo smoke). **Gap.** Evidence has not yet been collected
against **live bank UAT** systems. **To close:** follow the *Bank Developer UAT
Checklist* (UAT guide §17) per technology; record live-validated vs pending here.

## 4. External API pagination / rate limits — 🟡

**Now.** Integration adapters implement bounded pagination, retries with backoff,
timeouts, and classified errors. **Gap.** Vendor-specific **rate limiting** (HTTP
429 / `Retry-After`) and very large result-set paging are not fully generalized.
**To close:** add per-adapter 429/`Retry-After` handling and tune page sizes
against real tenant limits during UAT.

## 5. Kubernetes / OpenShift config requirements — ⛳

**Now.** K8s/OpenShift connectors read `kubeconfig`/context via env placeholders;
demo uses local context. **Gap.** Production needs real cluster access (kubeconfig
/ service-account tokens, RBAC to the namespaces in scope, network path from the
ECS runtime). **To close:** provision read-only cluster RBAC and wire kubeconfig
via the secret store; validate against UAT clusters.

## 6. Azure AD / OIDC production mapping — ⛳

**Now.** Demo runs with auth bypassed (`ECS_AUTH_ENABLED=false`); SharePoint/Graph
uses OAuth2 client-credentials (token via `authenticate()`), config-driven.
**Gap.** Production SSO (Azure AD / OIDC) app registration, redirect URIs, group→
role mapping, and Graph app permissions/consent are environment-specific. **To
close:** register the app in the bank tenant, map claims→ECS roles, grant least-
privilege Graph scopes, enable auth in prod. *(Out of scope for product code here;
auth/RBAC modules are intentionally untouched by this finalization.)*

## 7. Secrets manager required — ⛳

**Now.** Secrets resolve from environment variables (`.env.*` git-ignored); code
never logs secret values (SET/MISSING only). **Gap.** Production must source
secrets from a **managed secret store** (Vault / cloud secrets / K8s secrets) with
rotation. **To close:** integrate the chosen manager as the env source at
deploy/startup; enable rotation on the bank's schedule.

## 8. Monitoring / alerting required — ⛳

**Now.** Health endpoints exist (`/api/audit/health`, `/api/audit/integrations/health`)
and the demo smoke runner gives a PASS/FAIL gate. **Gap.** No metrics/log
aggregation/alerting wired. **To close:** export metrics (request rates/latency,
run success, adapter health), ship logs to the bank's platform, and alert on
health regressions and run failures.

## 9. HA / deployment pending — ⛳

**Now.** Runs as a single FastAPI app (`uvicorn app.main:app`); state is in-memory
per process. **Gap.** No multi-replica HA, no shared state across replicas, no
formal deploy manifests. **To close:** enable the durable store (item 1) so state
is shared, containerize + deploy (K8s/OpenShift) with ≥2 replicas behind the LB,
add readiness/liveness probes and rolling deploys.

## 10. Performance testing pending — 🟡

**Now.** APIs are bounded (safe default + hard-max pagination), responses are
paginated, and stores have retention caps; `test_audit_performance_safety.py` and
`test_audit_pagination_and_limits.py` assert bounded behavior. **Gap.** No
sustained **load/soak** testing at production data volumes. **To close:** run
load tests against realistic estate sizes; tune pagination, caching, and (with
Postgres) indexes/queries.

## 11. Data retention and audit-log policy pending — ⛳ (policy)

**Now.** In-memory stores apply pragmatic caps (retained runs, versions per key,
timeline/scheduler events). The SQL schema documents where retention is enforced.
**Gap.** A formal, bank-approved **retention & audit-log policy** (how long
evidence/observations/audit trails are kept, archival, legal hold, deletion) is
not yet defined or enforced. **To close:** agree the policy with Audit/Data
Governance; implement scheduled retention jobs against the durable store; log
retention actions to the audit trail.

---

## How to update this register

- Move an item to ✅ once it is provisioned **and** validated in the target
  environment (link the evidence: a passing check, a config PR, a UAT sign-off).
- Keep it honest and current — this register is a leadership-facing artifact
  (see [LEADERSHIP_DEMO_SCRIPT.md](LEADERSHIP_DEMO_SCRIPT.md) §5).
- Never place real IPs, hostnames, or secrets in this file.
