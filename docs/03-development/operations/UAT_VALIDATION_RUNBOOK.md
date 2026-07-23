# ECS UAT Validation Runbook

How to validate an ECS deployment in UAT: routes, connectors, predefined query
execution, audit intelligence, log collection, secret masking, and UAT sign-off.
Everything here is safe to run; no step requires committing secrets or real IPs.

> Prereq: ECS is running (see [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md)) and
> `.env.uat` is populated from the secret manager (git-ignored).

---

## 1. Start / confirm ECS is up

```bash
# If running locally for validation:
export ECS_ENV=uat; set -a; source .env.uat; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Confirm the process is healthy:
```bash
curl -fsS "http://127.0.0.1:8000/api/audit/health?role=owner&user=probe"
```

---

## 2. Validate routes

```bash
# Offline platform + route smoke (imports, route registration, adapter registry):
python scripts/run_production_smoke.py --strict
python scripts/run_production_smoke.py --base-url http://127.0.0.1:8000 --strict
```

Spot-check the key API + UI routes return 200 (not 404):
```bash
for p in /api/audit/dashboard /api/audit/assets /api/audit/mapping /api/audit/runs \
         /api/audit/repository /api/audit/observations /api/audit/packs \
         /api/audit/integrations /api/audit/health; do
  curl -s -o /dev/null -w "%{http_code}  $p\n" "http://127.0.0.1:8000$p?role=owner&user=probe"
done
```

---

## 3. Validate connectors (config-only, then live)

```bash
# Config-only (no network): confirms presence + masking for every adapter.
python scripts/run_uat_connector_health.py --adapter all --no-network

# Live probe for configured adapters (only hits endpoints that are configured):
python scripts/run_uat_connector_health.py --adapter all --live --strict
```

Expected: unconfigured adapters report `not_configured` (valid until credentials
are provisioned); configured adapters report `ok` when reachable + authenticated.
Use the printed remediation hints for any failures (see
[CONNECTOR_TROUBLESHOOTING_RUNBOOK.md](CONNECTOR_TROUBLESHOOTING_RUNBOOK.md)).

---

## 4. Validate predefined query execution

```bash
# Environment diagnostic for the predefined-query connectors (no docker check):
python3 scripts/check_predefined_extended_environment.py --no-docker-check
```

Then run a real, read-only baselining check against a UAT target and confirm the
evidence is captured (rows returned, no secret leakage in the excerpt). Review the
run in the UI: `/mvp/audit/evidence-runs`.

---

## 5. Validate audit intelligence

```bash
# Offline end-to-end walkthrough (catalog -> mapping -> run -> validation ->
# observation -> pack -> dashboard -> integrations):
python scripts/run_ecs_demo_smoke.py
```

Then in the UI confirm each surface renders with data:
`/mvp/audit/dashboard`, `/mvp/audit/technology-mapping`, `/mvp/audit/evidence-runs`,
`/mvp/audit/validation-results`, `/mvp/audit/observations`,
`/mvp/audit/repository`, `/mvp/audit/evidence-packs`, `/mvp/audit/executive-readiness`.

---

## 6. Collect logs

```bash
# systemd:
journalctl -u ecs --since "1 hour ago" --no-pager

# Docker Compose:
docker compose -f deploy/docker-compose.prod.example.yml logs --since 1h ecs-app

# Kubernetes:
kubectl logs deploy/ecs-app --since=1h
```

Save logs to the change ticket. **Verify logs contain no secret values** (only
`SET`/`MISSING` markers should appear for credentials).

---

## 7. Confirm secrets are masked

```bash
# Masked config for every adapter (secrets shown as SET/MISSING only):
curl -s "http://127.0.0.1:8000/api/audit/integrations?role=owner&user=probe"

# Health view must never echo a secret value:
python scripts/run_uat_connector_health.py --adapter all --json | \
  grep -iE "password|secret|token" || echo "no raw secrets in output (expected SET/MISSING only)"
```

Any occurrence of a real credential value is a **stop-ship** — investigate before
proceeding.

---

## 7a. Connector evidence ingestion (dry-run → live)

Connector *execution + evidence ingestion* is **opt-in and safe by default**: with
the flag off, nothing hits the network. Verify the chain end to end.

```bash
# 1) Dry-run (config-only; reports what WOULD run, NO network, NO secrets):
curl -s -X POST "http://127.0.0.1:8000/api/connectors/jira/dry-run?role=owner&user=probe"

# 2) Parser test (deterministic mock transport; validates the normalizer offline):
curl -s -X POST "http://127.0.0.1:8000/api/connectors/jira/parser-test?role=owner&user=probe"

# 3) Live collect — DISABLED by default. Enable explicitly for UAT collection:
export ECS_CONNECTOR_EXECUTION_ENABLED=true      # opt-in flag
#    (also requires the adapter to be configured via .env.uat)
curl -s -X POST "http://127.0.0.1:8000/api/connectors/jira/collect?role=owner&user=probe&framework=DPSC&application=Net%20Banking"
```

Expected:
- Flag **off** → `status: "skipped"` (no network).
- Flag **on** but adapter unconfigured → `status: "not_configured"` (still no network).
- Flag **on** + configured → evidence objects fetched, ingested, SHA-256 hashed, and
  mirrored into the audit-intelligence repository (`audit_repository_synced: true`).

The Connector Test Workbench UI (`/mvp/connectors/test-workbench`) runs all of the
above (config-status, health-check, dry-run, parser-test, collect) plus the
evidence-intelligence reports below — no CLI required.

## 7b. Evidence repository, completeness, quality, reuse & readiness

Confirm ingested evidence flows into the repository and the analytics surfaces.

```bash
# Evidence repository (stored artifacts + versions):
curl -s "http://127.0.0.1:8000/api/audit/repository?role=owner&user=probe"
curl -s "http://127.0.0.1:8000/api/audit/evidence/stats?role=owner&user=probe"

# Completeness (KPIs, gaps, missing-evidence rows):
curl -s "http://127.0.0.1:8000/api/evidence/completeness?role=owner&user=probe"

# Quality scoring (repository-wide summary + per-item):
curl -s "http://127.0.0.1:8000/api/evidence/quality?role=owner&user=probe"
curl -s "http://127.0.0.1:8000/api/evidence/<EVIDENCE_KEY>/quality?role=owner&user=probe"

# Reuse + readiness:
curl -s "http://127.0.0.1:8000/api/evidence-reuse/records?role=owner&user=probe"
curl -s "http://127.0.0.1:8000/api/evidence-reuse/readiness?role=owner&user=probe"
```

UI equivalents: `/mvp/completeness`, `/mvp/evidence-health`, `/mvp/reuse`,
`/mvp/evidence-story`, `/mvp/audit/executive-readiness`. After a live `collect`,
the ingested items should raise the repository count and appear in the quality
summary (`scored` > 0) and reuse/readiness views.

## 7c. Local LLM benchmark (16 GB and 20 GB laptops)

There are **only two live RAM profiles** — `local_16gb_safe` and
`local_20gb_extended` (plus a no-LLM `worst_case_enterprise_dry_run`). There is **no
28 GB / 60 GB profile.** All prompt actions have a deterministic dry-run/fallback,
so this is safe even without a local model.

```bash
# Dry-run (no model needed; validates prompts, token estimates, profile rules):
python scripts/run_audit_llm_benchmark.py --profile local_16gb_safe            # 16 GB
python scripts/run_audit_llm_benchmark.py --profile local_20gb_extended        # 20 GB

# LIVE (requires a local Ollama model per config/llm.yaml). Run each on the
# matching laptop; capture the JSON/markdown report under reports/:
python scripts/run_audit_llm_benchmark.py --profile local_16gb_safe --mode live
python scripts/run_audit_llm_benchmark.py --profile local_20gb_extended --mode live

# 16K/1K token validation on a 16 GB machine (measures real context usage):
python scripts/run_16k_1k_token_validation.py
```

Expected profile rules (enforced): 16 GB **blocks** 20K prompts (`extended_20k`);
20 GB **allows selected** 20K prompts (restricted, concurrency 1). The workbench UI
(`/mvp/audit/llm-workbench`) exposes classify / token-estimate / query / benchmark /
export; benchmark from the UI is always dry-run (use the CLI `--mode live` for live).

## 7d. Capture UAT screenshots / results

For each surface validated, capture evidence for the sign-off pack:

- **Screenshots** (browser): Dashboard (`/dashboard`), Predefined Queries, Connector
  Test Workbench (config-status + parser-test + collect result), Completeness,
  Evidence Health, Executive Readiness, LLM Prompt Workbench. Save as
  `uat/screenshots/<surface>_<YYYYMMDD>.png`.
- **API captures**: pipe the `curl` outputs above to files under
  `uat/results/<endpoint>_<YYYYMMDD>.json` (redact nothing — responses already carry
  no secrets; every response includes an `X-Request-ID` header for traceability).
- **Benchmark reports**: attach the generated files from `reports/` (LLM benchmark)
  and the connector health JSON (`--json`).

Record the ECS build (`git rev-parse --short HEAD`) and `ECS_ENV` with each capture.

---

## 8. UAT sign-off

Complete the *Bank Developer UAT Checklist* in
`docs/03-development/developer-manual/connectors/UAT_INTEGRATION_GUIDE.md` per target technology, then record:

- [ ] Routes validated (all 200, no 404).
- [ ] Connectors: configured adapters healthy; masking confirmed.
- [ ] Connector ingestion: dry-run + parser-test pass; live `collect` (flag on)
      produces SHA-256'd, audit-mirrored evidence for at least one configured adapter.
- [ ] Predefined query executed against a UAT target; evidence reviewed.
- [ ] Evidence intelligence: completeness %, quality summary, and reuse/readiness
      reflect ingested evidence.
- [ ] Local LLM benchmark run on 16 GB and 20 GB laptops; reports captured
      (only `local_16gb_safe` / `local_20gb_extended` profiles exist).
- [ ] Audit intelligence surfaces render with data.
- [ ] Screenshots + API/benchmark result captures saved to the sign-off pack.
- [ ] Logs collected; no secrets present.
- [ ] Sign-off recorded (who / when / scope) and gaps logged in
      `docs/03-development/production/PRODUCTION_READINESS_GAP_REGISTER.md`.
