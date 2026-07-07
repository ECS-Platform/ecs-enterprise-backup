# ECS Demo Runbook (Leadership Walkthrough)

A no-live-dependency runbook to demo the ECS Audit Intelligence platform to
leadership. Everything below runs offline (no bank systems, no live Docker
required for the core walkthrough).

---

## 0. Pre-flight (30 seconds)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off

# One-command health check of the whole platform (prints PASS/FAIL):
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py
```

Expect `10/10 checks passed -> ALL PASS` (catalog, services, discovery, mapping,
orchestration, validation, observations, packs, dashboard, integrations).

---

## 1. Talking track (the ECS story)

```
Technology  ->  Predefined Queries (Controls)  ->  Frameworks  ->  Evidence  ->  Audit Readiness
```

- **187 predefined controls** across **21 technologies** and **16 frameworks**.
- ECS discovers assets, fingerprints their technology, maps applicable controls,
  collects evidence, validates it deterministically, raises observations, stores
  versioned evidence, and packages audit-ready evidence packs — all surfaced in an
  executive dashboard.

---

## 2. CLI walkthrough (offline, no browser)

```bash
# Mapping (Technology -> Control -> Framework)
PYTHONPATH=. python scripts/audit_intelligence_report.py --section mapping
PYTHONPATH=. python scripts/audit_intelligence_report.py --section mapping --technology NGINX

# Asset inventory + fingerprints (docker-compose parsed offline; no daemon)
PYTHONPATH=. python scripts/audit_intelligence_report.py --section assets --docker-compose
```

---

## 3. UI walkthrough (local server)

```bash
./start_ecs.sh        # or: uvicorn app.main:app --port 8000
```

Open (append `?role=owner&user=AppOwner`):

| Page | URL |
|---|---|
| Executive Readiness (dashboard) | `/mvp/audit/executive-readiness` |
| Asset Inventory | `/mvp/audit/assets` |
| Technology Inventory | `/mvp/audit/technology-inventory` |
| Technology Mapping | `/mvp/audit/mapping` |
| Evidence Runs | `/mvp/audit/runs` |
| Evidence Repository | `/mvp/audit/repository` |
| Observations | `/mvp/audit/observations` |
| Evidence Packs | `/mvp/audit/packs` |
| Validation Results | `/mvp/audit/validation` |

The **Audit Intelligence** group also appears in the left sidebar.

---

## 4. REST API walkthrough

```bash
BASE="http://127.0.0.1:8000"; Q="role=owner&user=AppOwner"
curl -s "$BASE/api/audit/mapping/stats?$Q"
curl -s "$BASE/api/audit/assets?limit=10&$Q"
curl -s "$BASE/api/audit/dashboard?$Q"
curl -s "$BASE/api/audit/integrations/health?$Q"
# Start a mocked run (non-executable control -> Configuration Required, no live connector):
curl -s -X POST "$BASE/api/audit/runs?$Q" -H 'Content-Type: application/json' \
     -d '{"scope_kind":"control","scope_value":"NGX-001"}'
```

---

## 5. Optional: local Docker demo targets

Only needed to show *live* predefined-query execution (not required for the Audit
Intelligence demo):

```bash
docker compose --profile db-targets --profile infra-demo up -d
python3 scripts/check_predefined_technology_environment.py
python3 scripts/check_predefined_extended_environment.py
```

---

## 6. Talking points for approvers

- **Deterministic & governed:** validation is rule-based (no LLM), every verdict
  carries a `rule_id` + rationale; observations follow a controlled workflow.
- **Evidence integrity:** every evidence artifact is versioned with a SHA-256 hash;
  evidence packs ship a verifiable JSON manifest.
- **Enterprise-ready:** 11 integration adapters (ServiceNow, Archer, SharePoint,
  Teams, Outlook, Jira, Confluence, SonarQube, Checkmarx, Prisma Cloud, Tripwire),
  all config-driven with secret masking and graceful "not configured" behaviour.
- **Safe by default:** no live systems required; secrets never logged; startup
  never fails if optional integrations are absent.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `psycopg2` import error on a script | Use the venv with `requirements.txt` installed (needed only for live DB scripts). |
| A page/API 404 | Confirm the server restarted after pulling; check the URL table above. |
| Demo smoke FAIL | Re-run `python scripts/run_ecs_demo_smoke.py`; the failing check's detail names the cause. |
| Integrations show `not_configured` | Expected without `.env.uat`; set adapter env vars to configure. |
