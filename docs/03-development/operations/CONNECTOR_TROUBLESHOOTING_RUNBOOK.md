# ECS Connector Troubleshooting Runbook

Diagnose and remediate ECS enterprise integration connector issues (ServiceNow,
Archer, SharePoint/Graph, Jira, Confluence, SonarQube, Checkmarx, Prisma Cloud,
Tripwire). Safe to run; no secrets are printed and no live call is made unless you
explicitly pass `--live`.

---

## 1. First step — run the health harness

```bash
# Config-only (no network): what is configured, and is the config masked?
python scripts/run_uat_connector_health.py --adapter all --no-network

# Live probe for configured adapters only:
python scripts/run_uat_connector_health.py --adapter <name> --live
```

The harness prints, per adapter: `configured`, masked config (`SET`/`MISSING`),
`status`, `errors`, and a **remediation hint**. Statuses map to root causes below.

---

## 2. Status → cause → fix

| Status | Meaning | Likely cause | Fix |
|--------|---------|--------------|-----|
| `not_configured` | Required env vars missing | Credentials not set | Set the adapter's `ECS_*` vars (the hint lists them); re-run. |
| `auth_error` | 401/403 from the endpoint | Wrong/expired/insufficient credential | Rotate/fix the token/secret; confirm scope/permissions. |
| `timeout` | No response in time | VPN/routing down, endpoint slow | Confirm VPN + routing; raise `ECS_*_TIMEOUT_SECONDS`; retry. |
| `connection_error` | Cannot connect | Firewall/port/DNS | Open the port; confirm DNS/host; `nc -vz <host> <port>`. |
| `http_error` | Non-2xx HTTP | Wrong base URL / API path | Verify `ECS_*_BASE_URL`; check the vendor API version. |
| `health_error` | Adapter raised internally | Unexpected response shape | Capture the error type; check the endpoint + credentials. |
| `configured` (no `--live`) | Config present, not probed | — | Re-run with `--live` to confirm reachability. |

---

## 3. Per-adapter quick reference

| Adapter (`--adapter`) | Auth | Env vars |
|-----------------------|------|----------|
| `servicenow` | OAuth client-credentials | `ECS_SERVICENOW_BASE_URL`, `ECS_SERVICENOW_CLIENT_ID`, `ECS_SERVICENOW_CLIENT_SECRET` |
| `archer` | API token | `ECS_ARCHER_BASE_URL`, `ECS_ARCHER_API_TOKEN` |
| `graph` | OAuth (Azure AD) | `ECS_GRAPH_TENANT_ID`, `ECS_GRAPH_CLIENT_ID`, `ECS_GRAPH_CLIENT_SECRET`, `ECS_GRAPH_SITE_ID` |
| `jira` | Basic (email+token) | `ECS_JIRA_BASE_URL`, `ECS_JIRA_USERNAME`, `ECS_JIRA_API_TOKEN` |
| `confluence` | Basic (email+token) | `ECS_CONFLUENCE_BASE_URL`, `ECS_CONFLUENCE_USERNAME`, `ECS_CONFLUENCE_API_TOKEN` |
| `sonarqube` | Token | `ECS_SONARQUBE_BASE_URL`, `ECS_SONARQUBE_TOKEN` |
| `checkmarx` | OAuth client-credentials | `ECS_CHECKMARX_BASE_URL`, `ECS_CHECKMARX_CLIENT_ID`, `ECS_CHECKMARX_CLIENT_SECRET` |
| `prisma` | Access/secret key | `ECS_PRISMA_CLOUD_BASE_URL`, `ECS_PRISMA_CLOUD_ACCESS_KEY`, `ECS_PRISMA_CLOUD_SECRET_KEY` |
| `tripwire` | Basic (user+password) | `ECS_TRIPWIRE_BASE_URL`, `ECS_TRIPWIRE_USERNAME`, `ECS_TRIPWIRE_PASSWORD` |

---

## 4. Network path checks (from the ECS runtime / jump host)

```bash
nslookup <adapter-host>                 # DNS resolves over the VPN?
nc -vz <adapter-host> <port>            # TCP reachable (firewall/port open)?
curl -sS -o /dev/null -w "%{http_code}\n" https://<adapter-host>/   # endpoint up?
```

---

## 5. Golden rules

- **Never** paste real credentials into logs, tickets, or this repo. ECS only ever
  shows `SET`/`MISSING`.
- `not_configured` is a **valid** state until credentials are provisioned — it is
  not a failure in strict mode.
- Fix config in `.env.uat` / the secret store, **never** in YAML or code.
- Escalate persistent `auth_error` to the credential owner; persistent
  `connection_error`/`timeout` to network/firewall.
