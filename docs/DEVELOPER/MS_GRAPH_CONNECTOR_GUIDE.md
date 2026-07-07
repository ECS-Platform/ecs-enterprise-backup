# ECS Microsoft Graph Connector Guide (SharePoint / Teams / Outlook)

**Audience:** Developers/operators wiring the ECS Microsoft Graph evidence
connectors to a real Microsoft 365 tenant for UAT/production.
**Golden rules:** credentials come from the environment / secret store only (never
hard-coded, never logged); ECS reads **evidence metadata only** and never
downloads file/attachment contents by default; no live call happens in tests.

> Cross-refs: [ENTERPRISE_CONNECTOR_UAT_SETUP.md](ENTERPRISE_CONNECTOR_UAT_SETUP.md),
> [INTEGRATION_ADAPTERS_GUIDE.md](INTEGRATION_ADAPTERS_GUIDE.md),
> [UAT_INTEGRATION_GUIDE.md](UAT_INTEGRATION_GUIDE.md).

---

## 1. What ships

| Connector | Module | Evidence |
|-----------|--------|----------|
| Shared Graph base | `modules/operations/integrations/ms_graph_base.py` | OAuth2 + pagination foundation |
| SharePoint | `sharepoint_graph.py` | sites, drives, drive/folder items, file metadata |
| Teams | `teams_graph.py` | teams, channels, channel messages, tabs |
| Outlook | `outlook_graph.py` | mail folders, messages, attachment metadata |

All three share one Azure AD app registration and the shared Graph base.

---

## 2. Azure App Registration (one-time, by the tenant admin)

1. **Register an application** in Entra ID (Azure AD) → App registrations.
2. Note the **Directory (tenant) ID** and **Application (client) ID**.
3. Create a **client secret** (store it in the secret manager; never in Git).
4. Grant **application** (not delegated) Microsoft Graph permissions — read-only,
   least privilege for the evidence you collect:
   - SharePoint documents: `Sites.Read.All`, `Files.Read.All`.
   - Teams: `Team.ReadBasic.All`, `Channel.ReadBasic.All`,
     `ChannelMessage.Read.All`.
   - Outlook mail: `Mail.Read` (application). Consider scoping to specific
     mailboxes with an **application access policy** in Exchange Online.
5. **Grant admin consent** for the tenant.

> Use read-only permissions. ECS never writes to Graph and never requests
> `*.ReadWrite.*` scopes.

---

## 3. Configuration

Shared Graph credentials (all three connectors):

| Variable | Meaning |
|----------|---------|
| `ECS_GRAPH_TENANT_ID` | Directory (tenant) ID |
| `ECS_GRAPH_CLIENT_ID` | Application (client) ID |
| `ECS_GRAPH_CLIENT_SECRET` | Client secret (from the secret store) |
| `ECS_GRAPH_SCOPE` | Default `https://graph.microsoft.com/.default` |
| `ECS_GRAPH_AUTHORITY_URL` | Default `https://login.microsoftonline.com` (change for sovereign clouds) |
| `ECS_GRAPH_TIMEOUT_SECONDS` | Request timeout (default 30) |
| `ECS_GRAPH_MAX_RETRIES` | Bounded retries (default 2) |

Connector-specific:

| Connector | Variables |
|-----------|-----------|
| SharePoint | `ECS_GRAPH_SITE_ID`, `ECS_GRAPH_DRIVE_ID` (opt), `ECS_SHAREPOINT_SITE_HOSTNAME`, `ECS_SHAREPOINT_SITE_PATH`, `ECS_SHAREPOINT_FOLDER_PATH` |
| Teams | `ECS_TEAMS_TEAM_ID`, `ECS_TEAMS_CHANNEL_ID`, `ECS_TEAMS_MESSAGE_LIMIT` |
| Outlook | `ECS_OUTLOOK_USER_ID`, `ECS_OUTLOOK_MAIL_FOLDER`, `ECS_OUTLOOK_MESSAGE_LIMIT` |

Non-secret defaults may also live under the `connectors:` section of
`config/environments/<env>.yaml` (`ms_graph`, `sharepoint_graph`, `teams_graph`,
`outlook_graph`); secrets always resolve from the `*_env`/`ECS_GRAPH_*` variables.

---

## 4. Authentication (OAuth2 client-credentials)

- Token endpoint: `{authority}/{tenant_id}/oauth2/v2.0/token`.
- Grant: `client_credentials`; scope `…/.default`.
- The token is acquired via `client.authenticate()`, **cached per client
  instance**, and applied as `Authorization: Bearer <token>`.
- `auth_headers()` applies a configured/cached token only and performs **no
  implicit network call**; call `authenticate()` first (the `graph_*` helpers do
  this automatically). The token/secret is never logged.

```python
from modules.operations.integrations.sharepoint_graph import SharePointGraphClient, get_config
import httpx

def httpx_transport(method, url, headers, params, timeout=None):
    # For the token endpoint, send params as form-encoded; else as query params.
    if url.endswith("/oauth2/v2.0/token"):
        resp = httpx.request(method, url, headers=headers, data=params, timeout=timeout)
    else:
        resp = httpx.request(method, url, headers=headers, params=params, timeout=timeout)
    if resp.status_code in (401, 403):
        raise PermissionError(f"auth {resp.status_code}")
    resp.raise_for_status()
    return resp.json()

client = SharePointGraphClient(config=get_config(), transport=httpx_transport)
if client.is_configured():
    client.authenticate()
    docs = client.fetch_drive_items()      # normalized evidence metadata
```

---

## 5. Fetching evidence (metadata only)

### SharePoint
```python
client.fetch_sites()                       # list/search sites
client.resolve_site_by_path()              # {hostname}:/{site_path} -> site
client.fetch_drives()                      # document libraries
client.fetch_drive_items()                 # items at a drive root
client.fetch_folder_items("Evidence/2026") # items in a folder path
client.fetch_file_metadata(item_id)        # single item metadata (no content)
client.download_file_metadata_only(item_id) # explicit metadata-only accessor
```

### Teams
```python
client.fetch_teams(); client.fetch_channels(team_id)
client.fetch_channel_messages(team_id, channel_id, limit)
client.fetch_channel_tabs(team_id, channel_id)
```

### Outlook
```python
client.fetch_mail_folders(user_id)
client.fetch_messages(user_id, folder, limit)
client.fetch_message(user_id, message_id)
client.fetch_attachments_metadata(user_id, message_id)  # $select excludes contentBytes
```

Pagination follows Graph's `@odata.nextLink` automatically, bounded by
`max_items`/`max_pages`. Every method returns the standard envelope
`{ok, source, status, items, errors}` and never raises.

---

## 6. Normalized evidence shapes

- **SharePoint item**: `source, item_id, name, web_url, size, created_datetime,
  modified_datetime, created_by, modified_by, mime_type, parent_reference,
  is_folder, evidence_type`.
- **Teams message**: `source, message_id, subject, body_preview, from_user,
  created_datetime, importance, web_url, evidence_type`.
- **Outlook message**: `source, message_id, subject, sender, recipients,
  received_datetime, has_attachments, importance, body_preview, web_link,
  evidence_type`; **attachment**: `attachment_id, name, content_type, size,
  is_inline, last_modified` (metadata only).

---

## 7. Testing with mocked transports

No live Graph call is made in tests. Inject a transport that returns dicts:

```python
def transport(method, url, headers, params, timeout=None):
    if url.endswith("/oauth2/v2.0/token"):
        return {"access_token": "TEST"}
    return {"value": [{"id": "1", "name": "policy.pdf"}]}

client = SharePointGraphClient(config={...}, transport=transport)
```

See `tests/test_ms_graph_connectors.py`, `tests/test_sharepoint_graph_connector.py`,
`tests/test_teams_graph_connector.py`, `tests/test_outlook_graph_connector.py`.

---

## 8. Security notes

- Read-only application permissions; least privilege; scope Outlook to specific
  mailboxes via an Exchange application access policy where possible.
- Secrets in a secret manager / `.env.uat` only — never committed. ECS shows
  `SET`/`MISSING`, never secret values.
- Contents are never downloaded by default (metadata + hashes only), keeping
  evidence collection privacy-preserving and lightweight.

---

## 9. Known limitations

- No token refresh on expiry (token cached for the client lifetime; production
  should re-mint on 401).
- No Graph throttling (HTTP 429 / `Retry-After`) handling beyond generic retry.
- `fetch_sites` search vs. list depends on the `search` argument; large tenants
  should pass a search term.
