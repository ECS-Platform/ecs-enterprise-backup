# ECS Enterprise Integration Connectors — Deepening Guide

**Audience:** Bank developers wiring the ECS enterprise integration connectors
(SharePoint/Graph, Jira, Confluence, SonarQube, Checkmarx, Prisma Cloud, Tripwire)
from *skeleton* to *production*.
**Golden rules:** credentials come from the environment / secret store only;
never hard-code, never commit, never log a secret; no connector makes a real
network call in tests.

> Cross-refs: [UAT_INTEGRATION_GUIDE.md](UAT_INTEGRATION_GUIDE.md) (env-var
> precedence + UAT/PROD workflow), [README_DEVELOPER.md](README_DEVELOPER.md).

---

## 1. Purpose

The connectors under `modules/operations/integrations/` collect evidence from
enterprise systems (document stores, ticketing, AppSec, CSPM, file-integrity) and
normalize it into consistent ECS shapes. They are shipped as **config-driven
skeletons**: fully wired for configuration, masking, health checks, pagination,
retry/backoff, timeout handling and auth-header assembly — but the live HTTP
transport is *injected*, so nothing hits a network until you supply a production
client. Unit tests inject mock transports.

This guide documents the deepened behavior and the exact steps to take a connector
to production.

---

## 2. Connectors at a glance

| Connector | Module | Auth model | Auth header | Primary fetch | Normalized shape |
|-----------|--------|-----------|-------------|---------------|------------------|
| SharePoint / Microsoft Graph | `sharepoint_graph.py` | OAuth2 client-credentials (`authenticate()`) | `Authorization: Bearer <token>` | `fetch_documents()` | document |
| Jira | `jira.py` | Basic (email + API token) | `Authorization: Basic …` | `fetch_issues()`, `fetch_issue()` | ticket/issue |
| Confluence | `confluence.py` | Basic (email + API token) | `Authorization: Basic …` | `fetch_pages()` | page/document |
| SonarQube | `sonarqube.py` | Token (as Basic user, empty pw) | `Authorization: Basic <token>:` | `fetch_issues()`, `fetch_quality_gate()` | issue / quality-gate |
| Checkmarx | `checkmarx.py` | OAuth2 client-credentials, IAM (`authenticate()`) | `Authorization: Bearer <token>` | `fetch_scans()` | scan |
| Prisma Cloud | `prisma_cloud.py` | Access/secret key → `/login` JWT (`authenticate()`) | `x-redlock-auth: <jwt>` | `fetch_alerts()` | alert/finding |
| Tripwire | `tripwire.py` | Basic (username + password) | `Authorization: Basic …` | `fetch_policy_results()` | policy result |

All adapters extend `BaseAdapter` in `modules/operations/integrations/_base.py`
and share one response envelope (§5) and one retry/timeout mechanism (§6).

---

## 3. Configuration & environment variables

Each connector resolves config per field (first non-empty wins): the environment
variable, then the YAML block (`connectors`/`integrations` section), then a code
default. Placeholders like `${VAR}` are treated as *unset*.

| Connector | Environment variables |
|-----------|----------------------|
| SharePoint / Graph | `ECS_GRAPH_TENANT_ID`, `ECS_GRAPH_CLIENT_ID`, `ECS_GRAPH_CLIENT_SECRET`, `ECS_GRAPH_SITE_ID`, `ECS_GRAPH_DRIVE_ID` (opt), `ECS_GRAPH_ACCESS_TOKEN` (opt), `ECS_GRAPH_TOKEN_URL` (opt), `ECS_GRAPH_TIMEOUT_SECONDS`, `ECS_GRAPH_MAX_RETRIES` |
| Jira | `ECS_JIRA_BASE_URL`, `ECS_JIRA_USERNAME`, `ECS_JIRA_API_TOKEN`, `ECS_JIRA_TIMEOUT_SECONDS`, `ECS_JIRA_MAX_RETRIES` |
| Confluence | `ECS_CONFLUENCE_BASE_URL`, `ECS_CONFLUENCE_USERNAME`, `ECS_CONFLUENCE_API_TOKEN`, `ECS_CONFLUENCE_TIMEOUT_SECONDS`, `ECS_CONFLUENCE_MAX_RETRIES` |
| SonarQube | `ECS_SONARQUBE_BASE_URL`, `ECS_SONARQUBE_TOKEN`, `ECS_SONARQUBE_TIMEOUT_SECONDS`, `ECS_SONARQUBE_MAX_RETRIES` |
| Checkmarx | `ECS_CHECKMARX_BASE_URL`, `ECS_CHECKMARX_CLIENT_ID`, `ECS_CHECKMARX_CLIENT_SECRET`, `ECS_CHECKMARX_ACCESS_TOKEN` (opt), `ECS_CHECKMARX_TOKEN_URL` (opt), `ECS_CHECKMARX_TIMEOUT_SECONDS`, `ECS_CHECKMARX_MAX_RETRIES` |
| Prisma Cloud | `ECS_PRISMA_CLOUD_BASE_URL`, `ECS_PRISMA_CLOUD_ACCESS_KEY`, `ECS_PRISMA_CLOUD_SECRET_KEY`, `ECS_PRISMA_CLOUD_TOKEN` (opt), `ECS_PRISMA_CLOUD_TIMEOUT_SECONDS`, `ECS_PRISMA_CLOUD_MAX_RETRIES` |
| Tripwire | `ECS_TRIPWIRE_BASE_URL`, `ECS_TRIPWIRE_USERNAME`, `ECS_TRIPWIRE_PASSWORD`, `ECS_TRIPWIRE_TIMEOUT_SECONDS`, `ECS_TRIPWIRE_MAX_RETRIES` |

Non-secret defaults (base URLs, timeouts) may also live under the `connectors:`
section of `config/environments/<env>.yaml`. **Secrets must never be placed in a
committed YAML file** — only in `.env.*` (git-ignored) or a secret manager. See
`.env.example` for the full, commented list.

The `*_TOKEN`, `*_ACCESS_TOKEN` overrides let an upstream token broker supply a
pre-issued token so ECS skips the token exchange entirely.

---

## 4. The standard adapter interface

Every module exposes the same functions and a client class:

```python
get_config() -> dict                 # env/YAML resolution (reads secrets, never logs)
is_configured() -> bool              # all required fields present
masked_config(cfg=None) -> dict      # SET/MISSING only — safe to log/return
health_check() -> dict               # config- or transport-based readiness probe
normalize_*(record) -> dict          # raw API record -> ECS shape

class XxxClient(BaseAdapter):
    config: dict
    transport: Optional[Transport]   # inject a mock in tests / a real client in prod
    def is_configured(self) -> bool
    def masked_config(self) -> dict
    def auth_headers(self) -> dict    # built per request; never logged
    def fetch_*(...) -> dict          # standard response envelope
```

`masked_config()` and the client `__repr__` are **secret-safe**: they render
`SET` / `MISSING`, never the value. (The client dataclasses use
`@dataclass(repr=False)` so they inherit `BaseAdapter`'s masking repr — this stops
credentials from leaking into logs or tracebacks.)

---

## 5. Consistent response envelope

`fetch_*` and `health_check` never raise. They return:

```json
{
  "ok": true,
  "source": "jira",
  "status": "ok",
  "items": [ ... normalized records ... ],
  "errors": []
}
```

`status` vocabulary: `ok`, `empty`, `not_configured`, `auth_error`, `timeout`,
`connection_error`, `http_error`, `transport_error`. On failure `ok` is `false`,
`items` is empty, and `errors` carries a **non-sensitive** message. `health_check`
additionally returns `configured` and `masked_config`.

---

## 6. Reliability: retry, backoff, timeout

Implemented once in `_base.call_with_retry` and applied by `BaseAdapter._get`:

- **Bounded retries** — total attempts `= 1 + max_retries` (`ECS_*_MAX_RETRIES`,
  default 2). Exceptions are classified, never propagated.
- **Non-retryable failures** — `auth_error` and `not_configured` are *not* retried
  (they will not self-heal).
- **Exponential backoff** — `backoff_base * 2**attempt` between retries. Default
  base is `0.0` (instant, so tests never sleep); a production transport can raise
  it or override in config (`backoff_base_sec`).
- **Timeout** — `ECS_*_TIMEOUT_SECONDS` (default 30) is forwarded to transports
  that accept a `timeout` keyword. Simple 4-arg test mocks are called unchanged.

---

## 7. Pagination

Offset/limit pagination is centralized in `_base.collect_paginated`, driven by a
`page_getter(offset, limit)` per adapter. It stops on a short page, when
`max_items` is reached, or at a `max_pages` safety cap — deterministic and bounded.
SonarQube uses 1-based page numbers (`p = offset // limit + 1`); Graph uses
`$top`/`$skip`; the rest use `offset`/`limit`.

---

## 8. Authentication details (per connector)

- **Basic** (Jira, Confluence, Tripwire): `base64(user:secret)` built by
  `_base.basic_auth_header`; returns `{}` when unconfigured so no malformed header
  is emitted. The secret is only ever placed in the `Authorization` header, never
  in query params.
- **SonarQube token**: sent as the Basic *username* with an **empty password**
  (`base64("<token>:")`), per SonarQube convention.
- **OAuth2 client-credentials** (Graph, Checkmarx): `authenticate()` prefers a
  configured `access_token`, then a cached token, otherwise POSTs
  `grant_type=client_credentials` to the token endpoint via the injected transport
  and caches the result; the token is then applied as `Bearer`.
- **Prisma Cloud**: `authenticate()` POSTs the access/secret key to `/login`,
  receives a JWT, and (once cached) sends it in the `x-redlock-auth` header.

**Explicit vs implicit auth.** For the token-exchange connectors (Graph,
Checkmarx, Prisma Cloud), token acquisition is an **explicit** step: call
`client.authenticate()` once before fetching. `auth_headers()` applies only a
*configured or already-cached* token and performs **no implicit network call** —
this keeps header assembly side-effect-free and lets an injected transport handle
its own auth if you prefer. `authenticate()` is attempted at most once per client
(both success and failure are cached), so it is safe to call before every fetch.
Basic-auth connectors (Jira, Confluence, SonarQube, Tripwire) need no
`authenticate()` step — the header is derived directly from config. Tokens/secrets
are cached on the client instance and never logged.

---

## 9. Taking a connector to production

1. **Provide credentials** via `.env.*` or a secret manager (never commit them).
2. **Inject a real transport.** Implement the callable
   `(method, url, headers, params, timeout=None) -> dict` on top of `httpx`/
   `requests`, raising exceptions that classify correctly (timeout → a timeout
   error, 401/403 → `IntegrationAuthError`, etc.). Pass it as `transport=`.
3. **Authenticate (token-exchange connectors only).** For Graph / Checkmarx /
   Prisma Cloud call `client.authenticate()` once so ECS mints and caches the
   token. (Basic-auth connectors skip this.) Alternatively, let your transport
   attach auth and skip `authenticate()`.
4. **Verify readiness** with `health_check()` — expect `status == "ok"` when the
   probe endpoint responds.
5. **Fetch + normalize** using the `fetch_*` methods; consume the `items` list.
6. **Never** log the client's `config`, headers, or raw API payloads that may echo
   tokens.

Example — Basic-auth connector (no `authenticate()` needed):

```python
import httpx
from modules.operations.integrations.jira import JiraClient, get_config

def httpx_transport(method, url, headers, params, timeout=None):
    resp = httpx.request(method, url, headers=headers, params=params, timeout=timeout)
    if resp.status_code in (401, 403):
        raise PermissionError(f"auth {resp.status_code}")
    resp.raise_for_status()
    return resp.json()

client = JiraClient(config=get_config(), transport=httpx_transport)
if client.is_configured():
    result = client.fetch_issues(jql="project = OPS AND status != Done")
    for issue in result["items"]:
        ...
```

Example — token-exchange connector (explicit `authenticate()`):

```python
from modules.operations.integrations.prisma_cloud import PrismaCloudClient, get_config

client = PrismaCloudClient(config=get_config(), transport=httpx_transport)
if client.is_configured():
    client.authenticate()            # mints + caches the JWT (x-redlock-auth)
    result = client.fetch_alerts()
    for alert in result["items"]:
        ...
```

---

## 10. Testing guarantees

`tests/test_integration_connectors_deepening.py` verifies, with **only mock
transports (no real network)**:

- auth headers are assembled correctly and secrets never appear in query params;
- `masked_config()` and client `repr` never leak secret values;
- `is_configured()` gating and the `not_configured` response;
- OAuth/login token exchange, then the minted token applied to data requests;
- retry/backoff (including non-retryable auth), timeout passthrough, and error
  classification;
- offset/page pagination stop conditions;
- the standard response envelope on success and failure.

Run:

```bash
PYTHONPATH=. pytest tests/test_integration_connectors_deepening.py
python3 -m compileall modules/operations/integrations tests
```

---

## 11. Known limitations (skeleton)

- No live token refresh/expiry handling — a token is cached for the client's
  lifetime; production wiring should re-mint on expiry/401.
- Token exchange bodies are sent form/JSON-style via the transport abstraction; a
  production transport decides the exact content-type/encoding.
- No built-in rate-limit (HTTP 429 → `Retry-After`) handling beyond generic retry.
- Normalization maps a pragmatic subset of fields; extend `normalize_*` per audit
  need.
- ServiceNow and Archer adapters use an older standalone pattern and are
  intentionally **not** modified here; their (non-`BaseAdapter`) client `repr`
  masking is a separate follow-up.
