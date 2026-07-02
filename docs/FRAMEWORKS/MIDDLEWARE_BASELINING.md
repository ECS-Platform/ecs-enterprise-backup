# Framework Reference — Middleware Baselining **[Inferred/Target]**

**Status:** **Not a dedicated key in `FRAMEWORK_CATALOG`.** Documented as a target framework. Closest shipped coverage: middleware/container controls inside **OS Baselining** (e.g., "Middleware Patch Cadence", "Container Host Baseline", "API Gateway OS Hardening", "Container Runtime Security") and **AppSec**. Part of [Frameworks Library](README.md).

## Purpose
Harden middleware tiers (Tomcat, app servers, API gateways, message brokers, container runtimes) — currently assessed via OS Baselining controls; a dedicated framework is a Phase 2 target.

## Objectives
Middleware patch cadence, secure configuration, TLS/keystore hygiene, runtime/container security, admin console hardening.

## Controls (today via OS Baselining catalog)
Middleware Patch Cadence · Container Host Baseline · Container Runtime Security · API Gateway OS Hardening. **[Inferred/Target]** dedicated Tomcat/keystore/admin-console controls.

## Checklist (target)
- [ ] Middleware patch report + zero-day emergency log
- [ ] Tomcat/app-server secure config (TLS, manager app disabled)
- [ ] Container runtime/pod security standards
- [ ] Admin console access restricted + logged

## Evidence Requirements
Patch reports, config exports, runtime security policy exports. **Query-driven** via Tomcat/Linux connectors (see [Predefined Query Architecture](../OPERATIONS/ECS_PREDEFINED_QUERY_ARCHITECTURE.md)).

## Control & Evidence Reuse
Patch/config/runtime evidence reuse with **OS Baselining, AppSec, Cloud Security, PCI DSS**.

## Reporting / Sample
- **Executive/Audit/Risk:** rolled into OS baseline maturity until a dedicated framework is added.
- **Sample finding [Inferred]:** Tomcat manager app reachable → restrict + re-scan → Approved.
