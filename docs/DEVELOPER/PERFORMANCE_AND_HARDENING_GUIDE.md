# ECS Performance & Hardening Guide (Audit Intelligence)

Production-readiness improvements for the **Audit Intelligence** layer
(`/api/audit/*` REST + `/mvp/audit/*` UI): safe caching, response pagination,
a consistent API error model, empty-state safety, and demo/production
robustness.

Everything here is **additive** and covered by offline, deterministic tests. It
does **not** redesign audit intelligence, add product modules, or touch
integration adapters / the predefined-query catalog / auth / RBAC / Docker.

> This guide complements `PRODUCTION_HARDENING_GUIDE.md` (adapter-level
> timeouts/retries/health) and focuses on the API/service hardening added for
> performance and safety.

---

## 1. In-process caching (no Redis)

All caching is process-local — no external cache/service is introduced. The
shared utility lives in `modules/shared/utils/simple_cache.py`.

### 1.1 The TTL cache utility

`TTLCache` / `@cached` provide a small, thread-safe, TTL + bounded-size cache:

```python
from modules.shared.utils.simple_cache import cached

@cached(ttl_seconds=600, maxsize=1)
def expensive_catalog() -> dict:
    ...
```

Guarantees:

- **TTL expiry** — every entry self-expires, so data can never go stale
  indefinitely.
- **Bounded memory** — a hard `maxsize` per cache; eviction prefers expired
  entries, else the soonest-to-expire.
- **Thread-safe** — a lock guards each cache (sync FastAPI handlers run on a
  threadpool). The value factory runs *outside* the lock so a slow computation
  never blocks other cache users.
- **Never changes correctness** — a miss simply recomputes. Caching is a pure
  optimisation.

Ergonomics mirror `functools.lru_cache`: the decorated function exposes
`.cache`, `.cache_clear()`, and `.cache_stats()`.

### 1.2 What is cached

| Surface | What | TTL | Why safe |
| --- | --- | --- | --- |
| `mapping_service.technologies/frameworks/controls/graph/stats/filter_options` | Mapping **catalog derivation** | 600s, `maxsize=1` | Pure, deterministic projection over the static predefined-query catalog; never changes at runtime. |
| `dashboard_service.executive_readiness()` | Composite **dashboard summary** | 30s + explicit invalidation | Reads mutable stores; short TTL **and** invalidated on every known mutation, so it is never stale after a change. |

The engine-level control projection remains memoized via `functools.lru_cache`
in `technology_control_mapping._all_control_refs` (cleared by
`mapping.reset_cache()`).

### 1.3 Invalidation & reset hooks (for tests + admin)

- **Global:** `simple_cache.reset_all_caches()` clears **every** registered cache
  in the process (use in a fixture).
- **Mapping catalog:** `mapping_service.reset_cache()` clears the service caches
  and the engine `lru_cache`.
- **Dashboard:** `dashboard_service.invalidate_dashboard_cache()` (alias
  `reset_cache()`) drops cached dashboard payloads.

The dashboard cache is invalidated automatically (best-effort, never raises) from
the engine write/reset paths:

- `evidence_repository.store_evidence()` / `reset_repository()`
- `observation_generation.generate_observation()` / `transition()` / `reset_observations()`
- `evidence_orchestrator._store()` (create/execute) / `reset_runs()`

Force a fresh recompute without caching via
`dashboard_service.executive_readiness(use_cache=False)`.

---

## 2. Pagination & response limits

Large/list responses are **bounded** so a single request can never return an
unbounded payload or do unbounded work.

### 2.1 The contract

Helper: `_paginate(items, limit, offset)` in
`modules/audit_intelligence/routes/routes_audit_intelligence.py`.

- **Default limit:** `_DEFAULT_LIMIT = 200`.
- **Hard max:** `_MAX_LIMIT = 1000` (requests above this are clamped).
- Invalid `limit`/`offset` (non-numeric, negative, zero) → coerced to safe
  defaults. `None`/non-list inputs → treated as empty.
- Every paginated response carries a `page` object:

```json
{ "total": 523, "limit": 200, "offset": 0, "returned": 200, "has_more": true }
```

> Pagination query params are declared as **strings** at the API boundary
> (`limit: str = "200"`) so a bad value like `?limit=abc` is coerced to the
> default and returns a bounded **200** — instead of FastAPI rejecting it with a
> 422 before clamping runs.

### 2.2 Paginated endpoints

| Endpoint | Response key | Notes |
| --- | --- | --- |
| `GET /api/audit/assets` | `inventory` | also returns `coverage` (summary) + `elapsed_ms` |
| `GET /api/audit/evidence` | `evidence` | full filter set (query/technology/framework/asset/verdict/tag) |
| `GET /api/audit/repository` | `evidence` | **alias** of `/evidence` |
| `GET /api/audit/observations` | `observations` | filters: status/severity/framework/technology |
| `GET /api/audit/runs` | `runs` | |
| `GET /api/audit/mapping` | `results` | **alias** entry point; also returns `stats` |
| `GET /api/audit/mapping/search` | `results` | |
| `GET /api/audit/packs/{type}/{scope}` | `pack.items` | see below |

**Packs** are special: `item_count` and `pack_hash` are computed over the **full**
item set (so `verify_manifest` still works), while the response only carries a
bounded page of `items` plus an `items_page` metadata block. Pack identity is
never altered by pagination.

---

## 3. API error model

Every `/api/audit/*` handler is wrapped by `_safe`, and all error responses use a
single envelope.

### 3.1 Success

```json
{ "ok": true, "<payload-key>": ... }
```

### 3.2 Error

```json
{
  "ok": false,
  "status": "error",
  "message": "Unknown technology: Foo",
  "errors": ["Unknown technology: Foo"],
  "error": "Unknown technology: Foo"
}
```

- `error` is a **legacy alias** of `message`, retained for backward compatibility
  (do not remove without a client migration).
- Standard statuses: `404` (unknown resource), `400` (bad input / unsupported
  type), `500` (unexpected error).

### 3.3 Safe exception handling (`_safe`)

Any unhandled exception in a handler becomes a consistent JSON **500**:

```json
{ "ok": false, "status": "error", "message": "internal_error",
  "errors": ["<handler>: <ExceptionType>"], "error": "internal_error" }
```

Only the exception **type** is surfaced — never its message/args — so a secret
embedded in an error string can never leak to a client. **No stack traces are
ever returned.**

### 3.4 Route hardening: dashboard sections

`GET /api/audit/dashboard/{section}` resolves `section` against an explicit
**allow-list** (`_DASHBOARD_SECTIONS`). A path parameter can never resolve to
arbitrary module attributes (e.g. cache-reset hooks or imported helpers); an
unknown section returns 404.

---

## 4. Empty-state handling

Empty state is always **valid JSON**, never a crash:

- Empty repository / observations / runs → `{"ok": true, "<key>": [], "page": {...}}`.
- Empty stats/summaries → zero-valued objects (`0%`, empty maps), not errors.
- Empty packs → `item_count: 0`, `items: []`, valid `pack_hash`.
- Unknown resource (technology / framework / run / observation / adapter) →
  the error envelope with the right status code.
- Unsupported technology scope → empty search results and an empty pack that
  completes cleanly (never a 500).

---

## 5. Secret & logging safety

- Integration config is exposed **only** via `masked_config()` /
  `masked_config_all()`, which render secrets as `SET` / `MISSING` — never raw
  values.
- `/api/audit/integrations` and `/api/audit/integrations/health` reuse the masked
  views. Tests assert that fake secret env values never appear in the response
  body of the integrations, dashboard, repository, or runs endpoints.
- `_safe` never echoes exception messages, so a secret in an error string cannot
  reach a client or a log line built from the response.

---

## 6. Demo safety

- Repeated dashboard/mapping hits are **cheap and stable** (served from cache),
  keeping demos snappy under clicking-around.
- In-memory stores are capped so a long-running demo/process cannot grow without
  bound:
  - runs: `MAX_RETAINED_RUNS = 500` (oldest evicted),
  - evidence versions per key: `MAX_VERSIONS_PER_KEY = 50`,
  - timeline events: `MAX_TIMELINE_EVENTS = 5000`.
- No network calls in the default (skeleton) path; integration adapters require an
  injected transport, so demos and tests are fully offline.
- Default response limits bound payload sizes even when a caller omits `limit`.

---

## 7. Production hardening checklist

Before relying on the Audit Intelligence API in a shared/production environment:

- [ ] **Auth/RBAC enabled** (`ECS_AUTH_ENABLED=true`, demo mode off). This layer
      is additive to the existing auth; it does not bypass it.
- [ ] **Config validated** (`ECS_VALIDATE_CONFIG=on`) so misconfig fails fast.
- [ ] **Secrets from env/secret-manager only** — never hard-coded; confirm
      `/api/audit/integrations` shows `SET/MISSING`, never values.
- [ ] **Pagination defaults reviewed** — confirm `_DEFAULT_LIMIT` / `_MAX_LIMIT`
      suit your client; clients should paginate via `page.has_more`/`offset`.
- [ ] **Cache TTLs reviewed** — catalog TTL (600s) is safe for a static catalog;
      lower it if the catalog is hot-reloaded. Dashboard TTL (30s) balances
      freshness vs cost and is backed by explicit invalidation.
- [ ] **Durable stores** — the in-memory repository/observations/runs are for the
      demo/skeleton; wire durable persistence for production (public APIs are
      unchanged, so caching/pagination continue to apply).
- [ ] **Cache reset on deploy/catalog reload** — call `reset_all_caches()` (or the
      per-service `reset_cache()`) after a catalog hot-reload.
- [ ] **Monitoring** — track `elapsed_ms` on `/api/audit/assets`, cache
      `hits/misses` (`*.cache_stats()`), and 5xx rates.
- [ ] **Smoke tests green** — run the suite in §8 in CI.

---

## 8. Tests

Run the hardening + regression suite:

```bash
PYTHONPATH=. pytest \
  tests/test_audit_route_hardening.py \
  tests/test_audit_pagination_and_limits.py \
  tests/test_audit_performance_safety.py \
  tests/test_audit_intelligence_api.py \
  tests/test_audit_intelligence_ui.py
```

- `test_audit_route_hardening.py` — error envelope, `/api/audit/dashboard` +
  `/api/audit/repository` aliases, dashboard-section allow-list, empty-state,
  unsupported-technology, secret masking, `/mvp/audit/*` pages render.
- `test_audit_pagination_and_limits.py` — default/max limits, invalid-param
  safety, and pagination across assets/evidence/observations/runs/mapping/packs.
- `test_audit_performance_safety.py` — TTL cache behaviour, catalog + dashboard
  caching, dashboard invalidation on mutation/reset, bounded responses, and
  `_safe` graceful degradation (no secret leak on error).

Compile-check the touched trees:

```bash
python3 -m compileall modules/audit_intelligence modules/shared app tests
```

---

## 9. What was NOT changed

Auth / RBAC, benchmark modules, LLM modules, the predefined-query catalog +
engine, integration adapters (`modules/operations/integrations/`), connector
implementations, and Docker compose are **untouched**. All route registration and
service changes are additive and backward compatible.
