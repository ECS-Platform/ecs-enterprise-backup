# ECS End-to-End & Smoke Test Guide

All tests here are **deterministic and offline** — no live Docker, DB, network, or
bank systems. External calls use mocked transports / executors.

---

## 1. What is covered

| Test file | Covers |
|---|---|
| `tests/test_audit_intelligence_e2e_smoke.py` | Full pipeline: ServiceNow (mock) → discovery → fingerprint → mapping → orchestration (mock executor) → validation → observations → repository → pack → dashboard → REST API. Plus empty-state and unsupported-technology safety. |
| `tests/test_integration_adapters_mocked.py` | All 9 integration adapters: config, masking (no secret leakage), health, `fetch_*` normalization, not-configured, timeout/auth/retry classification, pagination. |
| `tests/test_uat_config_placeholders.py` | `.env.example` / `_base.yaml` / `uat.yaml` contain all adapter placeholders; no public IPs; no inline secrets; YAML valid. |
| `tests/test_ecs_demo_smoke.py` | The `scripts/run_ecs_demo_smoke.py` runner (10 checks) passes and emits valid JSON. |
| `tests/test_audit_intelligence_api.py` | `/api/audit/*` endpoints (mapping/assets/runs/repository/observations/packs/dashboard/integrations). |
| `tests/test_audit_intelligence_ui.py` | `/mvp/audit/*` pages render with the shared ECS shell + nav. |

---

## 2. Run the scoped suite

```bash
export DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off

PYTHONPATH=. pytest \
  tests/test_audit_intelligence_api.py \
  tests/test_audit_intelligence_ui.py \
  tests/test_audit_intelligence_e2e_smoke.py \
  tests/test_integration_adapters_mocked.py \
  tests/test_uat_config_placeholders.py \
  tests/test_ecs_demo_smoke.py

python3 -m compileall modules scripts tests
```

Do **not** run the full repository suite for these changes.

---

## 3. The demo smoke runner

```bash
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py         # text PASS/FAIL summary
PYTHONPATH=. python scripts/run_ecs_demo_smoke.py --json  # machine-readable
```

Exit code 0 when all 10 checks pass; 1 otherwise. Use it as a pre-demo gate or a
CI smoke step.

---

## 4. Environment flags used by tests

- `DEMO_MODE=true` — enables local demo behaviour.
- `ECS_AUTH_ENABLED=false` — auth bypass for TestClient route/UI tests.
- `ECS_VALIDATE_CONFIG=off` — skip strict startup config validation.

## 5. Conventions

- Inject a **mock transport** for any adapter (`fetch_*` → `{ok, source, status,
  items, errors}`).
- Inject a **mock executor** `(control_id, user) -> result_dict` into
  `evidence_orchestrator.execute_run(...)` so no live connector runs.
- Reset in-memory stores between tests: `orch.reset_runs()`,
  `repo.reset_repository()`, `obs.reset_observations()`, `mapping.reset_cache()`,
  `fp.reset_cache()`.
