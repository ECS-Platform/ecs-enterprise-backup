# ECS UAT Execution Checklist

A step-by-step, **operator-run** checklist for executing an ECS UAT cycle against
bank systems. It complements (does not replace) the connector-level
`UAT_INTEGRATION_GUIDE.md`; this file is the **execution runbook** a bank
developer/operator follows in order.

> Safety: never put real IPs, hostnames, or secrets in Git. Secrets live only in
> `.env.uat` (git-ignored) or the bank secret manager. ECS only ever displays
> `SET` / `MISSING` for secret presence.

Legend: ☐ not started · ☑ done · ⚠ blocked (note the blocker).

---

## Phase 0 — Prerequisites (per environment)

- [ ] Change/UAT window approved; stakeholders notified.
- [ ] Target list finalized (which technologies / integrations are in scope this cycle).
- [ ] A workstation or jump host with Python 3.12+ and repo access is available.

## Phase 1 — Network reachability

- [ ] **VPN connected** — on the bank VPN (or an approved jump host) that can reach
      the UAT subnets in scope.
- [ ] **DNS reachable** — each target FQDN resolves over the VPN
      (`nslookup <uat-host>` / `getent hosts <uat-host>`).
- [ ] **Ports opened** — the firewall allows your source → each target port
      (`nc -vz <uat-host> <port>` succeeds). Record any pending firewall requests.

## Phase 2 — Identity & credentials

- [ ] **Read-only service accounts created** — least-privilege accounts provisioned
      per target (DB read-only roles, read-only API tokens, read-only cluster RBAC).
      No write/admin scopes.
- [ ] Credentials received via an approved channel (secret manager / sealed hand-off).
- [ ] **Secrets stored outside Git** — placed only in `.env.uat` or the secret
      manager. Confirm `git status` shows **no** `.env.uat` and no secrets staged.

## Phase 3 — Configuration

- [ ] **`.env.uat` populated** — real UAT hosts/ports + service-account references
      for every in-scope target (values only in env, never in YAML/code/docs).
- [ ] Environment selected (`ECS_ENV=uat` or equivalent) and config loads without
      error (`ECS_VALIDATE_CONFIG=on` for a fail-fast check).
- [ ] Masked config sanity: `/api/audit/integrations` shows the expected adapters
      as `configured` with secrets as `SET` (never a raw value).

## Phase 4 — Diagnostics (offline + config)

- [ ] **Diagnostics run** — environment/connector diagnostics pass for each target
      (config resolves, base URLs reachable, auth mode correct). Capture output.
- [ ] Adapter health (config-only): `/api/audit/integrations/health` →
      `configured: true` for in-scope integrations; `not_configured` for the rest
      (expected, not an error).

## Phase 5 — Mocked smoke (safety net, no live calls)

- [ ] **Mocked smoke passed** — run the offline end-to-end smoke:
      ```bash
      PYTHONPATH=. python scripts/run_ecs_demo_smoke.py    # expect 10/10 ALL PASS
      ```
- [ ] If any check fails, STOP and fix before touching live systems.

## Phase 6 — Live connector smoke (read-only)

- [ ] **Live connector smoke passed** — run the connector/UAT health tooling against
      real UAT endpoints (read-only). Confirm each in-scope target returns `ok`
      (or a clearly classified, expected status). No writes are performed.
- [ ] Timeouts / retries behave (a slow target degrades cleanly, never hangs the run).

## Phase 7 — Evidence collection & review

- [ ] Run a scoped evidence collection for the in-scope technology/framework.
- [ ] **Evidence reviewed** — spot-check collected evidence: correct control,
      captured metadata + **content hash**, sensible verdict (Pass/Fail/Warning).
- [ ] Observations for any failures look correct (severity + recommendation).
- [ ] Build an evidence pack and **verify its manifest hash** (auditor-trust check).

## Phase 8 — Record results

- [ ] Update the per-technology status (live-validated vs pending) in the
      [PRODUCTION_READINESS_GAP_REGISTER.md](PRODUCTION_READINESS_GAP_REGISTER.md)
      (item 3, Live UAT validation).
- [ ] File any blockers (firewall, credentials, vendor limits) with owners + ETAs.
- [ ] Confirm no secrets/IPs leaked into logs, tickets, or committed files.

---

## Quick command reference

```bash
# Network
nslookup <uat-host>;  nc -vz <uat-host> <port>

# Offline safety net (no creds, no network)
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py

# Config-only adapter health (no live calls unless configured)
curl -s "http://127.0.0.1:8000/api/audit/integrations/health?role=owner&user=UAT" | jq .
```

> Never commit `.env.uat`, real hostnames/IPs, or secrets. This checklist and all
> ECS docs stay free of live-environment values.

---

### Cycle sign-off

| Operator | Environment | Date | Targets validated | Result |
|----------|-------------|------|-------------------|--------|
|          | uat         |      |                   |        |
