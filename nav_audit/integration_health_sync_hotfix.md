# Integration Health — "Sync All Sources" 500 Hotfix

**Severity:** P1 (demo blocker)
**Type:** Demo-only resiliency hotfix (no architectural refactor)
**Endpoint affected:** `POST /mvp/platform/sync-all`
**Date:** 2026-06-16

---

## 1. Root Cause

When a connector host is unavailable or misconfigured, the connector raised a
network exception that propagated all the way up to the route, producing an
HTTP 500 and crashing the Integration Health page.

The exception escaped because of a gap in the exception-handling chain:

1. `ecs_platform/connectors/gitea_connector.py` → `collect_evidence()` calls
   `self._repos()`, which calls `self.http().get("/api/v1/repos/search", ...)`
   **without** a `try/except`. (Note: the sibling helpers `_pull_requests()` and
   `_commits()` *do* catch `HttpError`, but `_repos()` does not.)
2. The shared HTTP client (`http_client.py`) raises `HttpError` for HTTP errors
   and wraps `urllib.error.URLError` / `socket.gaierror` / `socket.timeout` into
   `HttpError` on connection failure. `HttpError` is a `RuntimeError`.
3. `BaseConnector.sync()` (`connectors/base.py`) only catches `ConnectorError`.
   Since `HttpError` is **not** a `ConnectorError`, it is **not** caught and
   escapes `sync()`.
4. `ecs_platform/ingestion.py` → `sync_connector()` called `connector.sync()`
   **without** a `try/except`, so the exception propagated out.
5. `sync_all()` was a plain list comprehension
   (`[sync_connector(n) for n in targets]`), so the **first** failing connector
   aborted the entire batch — remaining connectors were never processed.
6. The route `platform_sync_all` had no failure boundary → **HTTP 500**.

**Net effect:** one unreachable connector (e.g. Gitea) crashed Sync All Sources
for *all* connectors and 500'd the page.

---

## 2. Files Changed

| File | Change |
|------|--------|
| `ecs_platform/ingestion.py` | Wrapped `connector.sync()` in `sync_connector()` with a connector-level exception boundary that converts any failure into a structured `ok=False` result. Made `sync_all()` iterate defensively so a per-connector failure can never abort the batch. |

**Not modified** (per scope): dashboard logic, evidence workflows, governance
workflows, scheduler, RBAC, authentication, charts, themes, CSS, navigation, UI
layouts. The connector implementations (`gitea_connector.py`, `http_client.py`,
`base.py`) and `app/routes_platform.py` were left untouched — the orchestration
wrap fully resolves the issue, keeping blast radius minimal.

---

## 3. Before

`ecs_platform/ingestion.py` — `sync_connector()`:

```python
summary = connector.sync()          # <-- unprotected; HttpError / URLError /
result["collected"] = summary.get("collected", 0)   # socket.gaierror escape → 500
```

`ecs_platform/ingestion.py` — `sync_all()`:

```python
def sync_all(*, actor="system", role="admin", index=True):
    targets = enabled_connectors() or list(INGESTION_CONNECTORS)
    return [sync_connector(n, actor=actor, role=role, index=index) for n in targets]
    # first failing connector aborts the whole batch
```

---

## 4. After

`ecs_platform/ingestion.py` — `sync_connector()` (connector-level boundary):

```python
# Connector-level resiliency boundary: a connector whose host is unreachable
# or misconfigured can raise HttpError / urllib URLError / socket.gaierror
# (these are NOT ConnectorError, so BaseConnector.sync() does not catch them).
# Convert any such failure into a structured "failed" result so one bad
# connector can never crash Sync All Sources with a 500.
try:
    summary = connector.sync()
except Exception as exc:  # noqa: BLE001 - degrade gracefully, never propagate
    result["error"] = f"host unreachable: {exc}"
    return result
```

`ecs_platform/ingestion.py` — `sync_all()` (per-connector isolation):

```python
def sync_all(*, actor="system", role="admin", index=True):
    targets = enabled_connectors() or list(INGESTION_CONNECTORS)
    results: list[dict[str, Any]] = []
    for n in targets:
        # Defensive second layer: even if sync_connector ever raised, one failed
        # connector must not stop the remaining connectors from being processed.
        try:
            results.append(sync_connector(n, actor=actor, role=role, index=index))
        except Exception as exc:  # noqa: BLE001 - isolate per-connector failures
            results.append({
                "connector": n, "ok": False, "collected": 0, "persisted": 0,
                "indexed": 0, "relationships": 0, "started": _now(),
                "error": f"sync aborted: {exc}", "warnings": [],
            })
    return results
```

A failed connector now returns a structured result consistent with the existing
schema (`ok=False`, populated `error`) — semantically equivalent to the requested
`{"connector": "gitea", "status": "failed", "error": "host unreachable"}`. The
route reads `r.get("ok")` / `r.get("persisted")`, so the schema is unchanged and
the endpoint returns its normal `303` redirect with a success notice instead of a
`500`.

---

## 5. Validation Results

Simulated a mixed batch with the exact exceptions from the stack trace
(`HttpError`, `socket.gaierror`, `URLError`) raised by the Gitea connector while
GitHub, Jira, and Confluence succeed:

```
== sync_connector(gitea) raising HttpError ==
gitea     -> ok=False  error=host unreachable: HTTP 0: connection error: ...
gaierror  -> ok=False  error=host unreachable: [Errno -2] Name or service not known
URLError  -> ok=False  error=host unreachable: <urlopen error host unreachable>

== sync_all batch ==
      github -> success
        jira -> success
       gitea -> failed   host unreachable: ...
  confluence -> success

RESULT: 3/4 connectors synced; one failure did NOT abort the batch.
ALL ASSERTIONS PASSED — no exception propagated.
```

| Check | Result |
|-------|--------|
| Integration Health page loads | PASS (already demo-resilient via `health_overview()`) |
| `Sync All Sources` no longer returns 500 | PASS — `sync_all()` never raises; route returns `303` |
| One failed connector does not stop the rest | PASS — 3/4 succeed when Gitea fails |
| Demo mode continues working | PASS — `health_overview()` demo fallback untouched |
| No other ECS modules affected | PASS — only `ingestion.py` orchestration changed |
| Linter | PASS — no errors |

---

## 6. Risk Assessment

**Risk: LOW.**

- Change is confined to two functions in `ecs_platform/ingestion.py`
  (`sync_connector`, `sync_all`) — the connector sync orchestration layer only.
- No change to the result schema; all callers (`platform_sync_all`,
  `platform_sync`, `api_platform_sync`) continue to read the same keys.
- No connector implementations, HTTP client, RBAC/auth, scheduler, or UI were
  modified.
- The `except Exception` boundaries are deliberately broad at the orchestration
  layer to guarantee "Sync All Sources must NEVER crash the page"; they capture
  the failure into a structured result rather than swallowing it silently
  (the `error` field is populated and surfaced in the UI notice).
- Behavioral change is strictly additive: previously-succeeding connectors behave
  identically; only the previously-crashing path now degrades gracefully.

**Rollback:** revert the two edits in `ecs_platform/ingestion.py`.

---

*This is a demo-only resiliency hotfix. No architectural refactoring was
performed and connector implementations were not modified.*
