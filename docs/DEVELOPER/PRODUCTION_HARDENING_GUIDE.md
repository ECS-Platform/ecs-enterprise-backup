# ECS Production Hardening Guide (Audit Intelligence)

Hardening applied to the Audit Intelligence layer and integration adapters, without
changing the architecture. All behaviour is additive and covered by offline tests.

---

## 1. Consistent error model

- **REST:** `/api/audit/*` handlers return `{"ok": false, "error": "...", ...}`.
  Every non-trivial handler is wrapped by `_safe`, which converts any unexpected
  exception into a consistent `500 {"ok": false, "error": "internal_error",
  "detail": "<handler>: <ExcType>"}` — **no stack traces, no secret leakage**.
- **Adapters:** `fetch_*` never raise; failures are classified into the status
  vocabulary (`not_configured` / `auth_error` / `timeout` / `connection_error` /
  `http_error` / `transport_error`) inside `{ok, source, status, items, errors}`.

## 2. Secret masking

- `masked_config()` on every adapter and `masked_config_all()` in the registry
  return secrets as `SET` / `MISSING` only.
- Diagnostics and health endpoints reuse the masked views — **no passwords/tokens
  in logs or API responses** (covered by `test_masked_config_all_never_leaks_secrets`).

## 3. Timeouts, retries, backoff

- Default timeout: `DEFAULT_TIMEOUT_SEC = 30` (overridable per adapter via
  `ECS_*_TIMEOUT_SECONDS`).
- `call_with_retry` applies bounded retries (default 2) with exponential backoff.
  Retryable: timeout / connection / http. Non-retryable: auth / not-configured.

## 4. Graceful / safe empty states

- Missing configuration → `not_configured` response (never a crash).
- Empty inventory / repository / observations → valid empty payloads; dashboards
  compute 0%/empty rather than erroring (covered by e2e empty-state tests).
- Unsupported technology scope → an empty run that completes cleanly.
- **Startup never fails** if optional integrations are absent (registry catches
  per-adapter import/health errors).

## 5. Health checks

- Per-adapter: `health_check()` → `{ok, source, status, configured, masked_config, ...}`.
- Registry: `health_check_all()` → totals + per-adapter results.
- REST: `GET /api/audit/integrations/health`, `GET /api/audit/integrations/{name}/health`.

## 6. Performance safeguards (in-process only; no Redis)

- Mapping catalog derivation is memoized (`functools.lru_cache`), cleared via
  `reset_cache()`.
- The predefined catalog is loaded once and reused (engine caches it); request
  handlers do not reload the Excel workbook.
- In-memory stores are capped: runs (`MAX_RETAINED_RUNS = 500`, oldest evicted),
  evidence versions per key (`MAX_VERSIONS_PER_KEY = 50`), timeline events
  (`MAX_TIMELINE_EVENTS = 5000`).
- Heavy list APIs (`/api/audit/assets`, `/api/audit/evidence`) support
  `limit`/`offset` pagination (clamped to `≤ 1000`) and return `page` metadata;
  `/api/audit/assets` also returns `elapsed_ms` timing.

## 7. What was NOT changed

- Auth / RBAC, benchmark, LLM modules, the predefined-query catalog/engine, and the
  connector architecture are untouched. Route registration is additive.

## 8. Tests

`tests/test_integration_adapters_mocked.py` (masking, health, error classification,
retry, pagination), `tests/test_audit_intelligence_api.py` (error/empty/404 paths),
`tests/test_audit_intelligence_e2e_smoke.py` (empty-state + unsupported-tech safety).
