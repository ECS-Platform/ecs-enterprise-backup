# Microsoft Graph / SharePoint / Teams — UAT Testing Guide

**Purpose:** How to configure and test the ECS Microsoft Graph connectors
(SharePoint, Teams, Outlook) against a **real Microsoft 365 tenant** in UAT —
using the **existing** config surfaces and env variables. No connector code or
config is duplicated. **No secret ever goes in code or committed YAML.**

> Cross-refs: [uat_ip_configuration_guide.md](../operations/uat_ip_configuration_guide.md),
> [DEVELOPER/MS_GRAPH_CONNECTOR_GUIDE.md](MS_GRAPH_CONNECTOR_GUIDE.md),
> [DEVELOPER/ENTERPRISE_CONNECTOR_UAT_SETUP.md](../connectors/ENTERPRISE_CONNECTOR_UAT_SETUP.md).

---

## 1. Azure App Registration prerequisites (one-time, by the tenant admin)

1. **Register an application** in Entra ID (Azure AD) → App registrations.
2. Record the **Directory (tenant) ID** and **Application (client) ID**.
3. Create a **client secret** — store it in the secret manager, **never** in Git.
4. Grant **application** (not delegated) Microsoft Graph permissions (read-only,
   least privilege — see §2) and **grant admin consent**.
5. Identify the target **SharePoint site**, **Teams team/channel**, and (if used)
   the **Outlook mailbox (user id/UPN)**.

---

## 2. Required Graph permissions (read-only, least privilege)

| Connector | Application permissions |
|-----------|-------------------------|
| SharePoint (evidence documents) | `Sites.Read.All`, `Files.Read.All` |
| Teams (governance channels/messages) | `Team.ReadBasic.All`, `Channel.ReadBasic.All`, `ChannelMessage.Read.All` |
| Outlook (approvals mailbox — metadata only) | `Mail.Read` (consider scoping to specific mailboxes via an Exchange application access policy) |

ECS never requests `*.ReadWrite.*` and never downloads file/attachment **contents**
by default (metadata + hashes only).

---

## 3. Environment variables (canonical — what the adapters read)

Set these in your git-ignored `.env.uat` (or the secret manager). These are the
variables the Graph adapters actually consume (resolved by
`config/environments/uat.yaml` → `connectors.ms_graph` / `sharepoint_graph` /
`teams_graph` / `outlook_graph`):

```bash
# --- Shared Microsoft Graph (SharePoint + Teams + Outlook) ---
export ECS_GRAPH_TENANT_ID=<uat-tenant-id>
export ECS_GRAPH_CLIENT_ID=<uat-app-client-id>
export ECS_GRAPH_CLIENT_SECRET=<from-secret-manager>       # never commit
export ECS_GRAPH_SCOPE=https://graph.microsoft.com/.default
export ECS_GRAPH_AUTHORITY_URL=https://login.microsoftonline.com

# --- SharePoint ---
export ECS_GRAPH_SITE_ID=<uat-sharepoint-site-id>
export ECS_GRAPH_DRIVE_ID=<uat-drive-id-optional>
export ECS_SHAREPOINT_SITE_HOSTNAME=<tenant>.sharepoint.com
export ECS_SHAREPOINT_SITE_PATH=sites/<site-name>
export ECS_SHAREPOINT_FOLDER_PATH=ECS-UAT-Evidence

# --- Teams ---
export ECS_TEAMS_TEAM_ID=<uat-team-id>
export ECS_TEAMS_CHANNEL_ID=<uat-channel-id>

# --- Outlook (optional; metadata only) ---
export ECS_OUTLOOK_USER_ID=<uat-mailbox-upn-or-id>
export ECS_OUTLOOK_MAIL_FOLDER=inbox
```

> **Alternate names in `config/integrations.yaml`.** The general integrations file
> references `MS_TENANT_ID` / `MS_CLIENT_ID` / `MS_CLIENT_SECRET` (+ `SHAREPOINT_SITE_ID`)
> for its `sharepoint`/`teams` blocks. If you enable those, set that family too.
> The task's `MS_GRAPH_*` / `MS_TEAMS_*` names are conceptual aliases — map them to
> the **actual** `ECS_GRAPH_*` / `ECS_TEAMS_*` (and `MS_*`) variables above; do not
> introduce a third set.

The config values themselves stay in committed YAML as `${VAR}` / `*_env`
references only — see `config/environments/uat.yaml`:

```yaml
connectors:
  ms_graph:
    tenant_id:         "${ECS_GRAPH_TENANT_ID:-}"
    client_id:         "${ECS_GRAPH_CLIENT_ID:-}"
    client_secret_env: ECS_GRAPH_CLIENT_SECRET     # env NAME, never a value
    authority_url:     "${ECS_GRAPH_AUTHORITY_URL:-https://login.microsoftonline.com}"
  sharepoint_graph: { site_id: "${ECS_GRAPH_SITE_ID:-}", site_hostname: "${ECS_SHAREPOINT_SITE_HOSTNAME:-}", ... }
  teams_graph:      { team_id: "${ECS_TEAMS_TEAM_ID:-}", channel_id: "${ECS_TEAMS_CHANNEL_ID:-}" }
```

### Requested connector-config shape → where it lives

The requested `microsoft_graph` / `sharepoint` / `teams` YAML shape already exists,
expressed via the `connectors:` blocks above and `config/integrations.yaml`.
Reuse those — do not create a parallel connector file. The mapping is:

| Requested key | Actual ECS surface |
|---------------|--------------------|
| `microsoft_graph.tenant_id_env` | `connectors.ms_graph.tenant_id` (`${ECS_GRAPH_TENANT_ID}`) |
| `microsoft_graph.client_secret_env` | `connectors.ms_graph.client_secret_env: ECS_GRAPH_CLIENT_SECRET` |
| `microsoft_graph.authority_url` | `connectors.ms_graph.authority_url` |
| `microsoft_graph.graph_base_url` | `integrations.yaml` `sharepoint/teams.base_url` (`${MS_GRAPH_URL:-https://graph.microsoft.com/v1.0}`) |
| `sharepoint.site_url` | `ECS_SHAREPOINT_SITE_HOSTNAME` + `ECS_SHAREPOINT_SITE_PATH` (or `ECS_GRAPH_SITE_ID`) |
| `sharepoint.evidence_root_folder` | `ECS_SHAREPOINT_FOLDER_PATH` |
| `teams.team_id` / `channel_id` | `ECS_TEAMS_TEAM_ID` / `ECS_TEAMS_CHANNEL_ID` |

---

## 4. Token validation steps

```bash
export ECS_ENV=uat; set -a; source .env.uat; set +a

# Config-only (no network) — confirms creds are SET (masked), never printed:
python scripts/run_uat_connector_health.py --adapter graph --no-network
python scripts/validate_uat_config.py --assets config/uat_assets.uat.yaml \
  --connectors config/integrations.yaml --mode uat

# Live token exchange + probe (once creds are real):
python scripts/run_uat_connector_health.py --adapter graph --live
python scripts/run_uat_connector_health.py --adapter all --live
```

Programmatic token check (client-credentials against the tenant):
```python
from modules.operations.integrations.sharepoint_graph import SharePointGraphClient, get_config
import httpx

def transport(method, url, headers, params, timeout=None):
    if url.endswith("/oauth2/v2.0/token"):
        r = httpx.request(method, url, headers=headers, data=params, timeout=timeout)
    else:
        r = httpx.request(method, url, headers=headers, params=params, timeout=timeout)
    if r.status_code in (401, 403): raise PermissionError(f"auth {r.status_code}")
    r.raise_for_status(); return r.json()

c = SharePointGraphClient(config=get_config(), transport=transport)
assert c.is_configured(), "Graph creds missing (set ECS_GRAPH_* in .env.uat)"
print("token acquired:", bool(c.authenticate()))   # True on success; never prints the token
```

---

## 5. SharePoint test steps

1. Ensure `ECS_GRAPH_*` + `ECS_GRAPH_SITE_ID` (or `ECS_SHAREPOINT_SITE_HOSTNAME`
   + `ECS_SHAREPOINT_SITE_PATH`) are set.
2. **Config/health:**
   ```bash
   curl -s "http://127.0.0.1:8000/api/audit/integrations/sharepoint_graph/health?role=owner&user=UAT"
   ```
   Expect `configured: true` with masked config (SET/MISSING) — no secret values.
3. **Live fetch (metadata only):**
   ```python
   from modules.operations.integrations.sharepoint_graph import SharePointGraphClient, get_config
   c = SharePointGraphClient(config=get_config(), transport=transport)  # transport from §4
   c.authenticate()
   print(c.resolve_site_by_path())        # {hostname}:/{site_path} -> site
   print(c.fetch_drives())                 # document libraries
   print(c.fetch_folder_items("ECS-UAT-Evidence"))   # evidence-folder items (metadata)
   ```
4. **Expected:** normalized document metadata (`item_id`, `name`, `web_url`, `size`,
   `created_datetime`, `modified_datetime`, `created_by`, `mime_type`, …). Contents
   are never downloaded.
5. **UI:** open `/mvp/integrations` → SharePoint shows healthy/configured.

---

## 6. Teams test steps

1. Ensure `ECS_GRAPH_*` + `ECS_TEAMS_TEAM_ID` (+ `ECS_TEAMS_CHANNEL_ID`) are set.
2. **Config/health:**
   ```bash
   curl -s "http://127.0.0.1:8000/api/audit/integrations/teams_graph/health?role=owner&user=UAT"
   ```
3. **Live fetch:**
   ```python
   from modules.operations.integrations.teams_graph import TeamsGraphClient, get_config
   c = TeamsGraphClient(config=get_config(), transport=transport)  # transport from §4
   c.authenticate()
   print(c.fetch_channels())                                   # channels for the team
   print(c.fetch_channel_messages())                           # governance messages (preview)
   print(c.fetch_channel_tabs())                               # channel tabs
   ```
4. **Expected:** normalized channel/message metadata (`channel_id`, `message_id`,
   `subject`, `body_preview`, `from_user`, `created_datetime`, `web_url`, …).
5. **UI:** open `/mvp/integrations` → Teams shows healthy/configured.

---

## 7. Common errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `not_configured` | `ECS_GRAPH_TENANT_ID`/`CLIENT_ID`/`CLIENT_SECRET` (or `ECS_TEAMS_TEAM_ID` / `ECS_GRAPH_SITE_ID`) unset | Set them in `.env.uat`; re-run health `--no-network` to confirm SET |
| `auth_error` (401/403) on token | Wrong tenant/client/secret, or admin consent not granted | Verify app registration + client secret; grant admin consent for the Graph app permissions |
| `403` on fetch (token OK) | Missing Graph **application** permission (e.g. `Sites.Read.All`) | Add the permission (§2) + admin consent |
| `timeout` / `connection_error` | Network/VPN/proxy blocks `graph.microsoft.com` or `login.microsoftonline.com` | Confirm egress to Graph + login endpoints; raise `ECS_GRAPH_TIMEOUT_SECONDS` |
| SharePoint site not found | `ECS_GRAPH_SITE_ID` wrong, or `site_hostname`/`site_path` mismatch | Resolve the site id via Graph (`/sites/{hostname}:/{path}`); set `ECS_GRAPH_SITE_ID` |
| Teams messages empty | `ECS_TEAMS_CHANNEL_ID` missing or `ChannelMessage.Read.All` not consented | Set the channel id; grant the message permission |
| Secret appears in output | Misconfiguration | Stop — ECS never prints secrets; masked config shows SET/MISSING only. Investigate before proceeding |

---

## 8. No-secret-in-code policy

- Secrets live **only** in `.env.uat` (git-ignored) or the secret manager, and are
  referenced from YAML by `${VAR}` / `*_env` **names**, never values.
- ECS logs and masked-config endpoints (`GET /api/audit/integrations`,
  `/integrations/health`) show `SET`/`MISSING` only. Adapter `repr` is secret-safe.
- `scripts/validate_uat_config.py` fails the build if a connector field that looks
  like a secret carries an inline value instead of an env reference.
- Never paste tenant IDs, client secrets, or tokens into commits, tickets, docs,
  or screenshots.

---

## 9. UAT sign-off (Graph)

- [ ] App registered; read-only Graph permissions granted + admin-consented.
- [ ] `ECS_GRAPH_*` (+ SharePoint/Teams/Outlook vars) set in `.env.uat`.
- [ ] `validate_uat_config.py --mode uat` passes (no localhost, secrets via env).
- [ ] `run_uat_connector_health.py --adapter graph --live` → healthy.
- [ ] SharePoint + Teams live fetch returns normalized metadata (no contents).
- [ ] No secret values in any UI/API/log output.
