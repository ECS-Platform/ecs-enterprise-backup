# Connector Frontend Manual Testing Guide

**Status:** Current · **Owner:** Platform / Integrations
**Companion doc:** [`connector_frontend_testing_matrix.md`](connector_frontend_testing_matrix.md)

This guide gives step-by-step **manual frontend test cases** for the ECS enterprise
connectors using the **Connector Test Workbench**. Every action here is **read-only and
safe** — health check, config status, dry-run, and a **mock parser test** (deterministic
synthetic data, **no network call, no secrets**).

---

## 0. Prerequisites (all tests)

1. Start ECS locally (demo mode is fine):
   ```bash
   PYTHONPATH=. DEMO_MODE=true uvicorn app.main:app --reload
   ```
2. Open the workbench:
   - **URL:** `http://localhost:8000/connectors/test-workbench`
   - Alias: `http://localhost:8000/mvp/connectors/test-workbench`
3. You should see a **Connector** dropdown (11 connectors), an **Environment profile**
   selector (`local` / `UAT`), a config badge, and four action buttons:
   **Config status**, **Run health check**, **Dry-run evidence pull**, **Run parser test (mock)**.

**Understanding results**

- The **status chip** (top-right of the Result panel) shows `ok` (green), the connector
  status, or `error` (red).
- **Config status** returns masked config (`SET`/`MISSING`) — never a secret value.
- **Health check** reflects whether the connector is configured (config-based; no live call).
- **Parser test (mock)** always exercises the real parser path against synthetic data and
  should return `evidence_objects_detected ≥ 1` and a JSON preview.

**General pass/fail**

- **Pass:** HTTP 200, JSON renders in the output panel, no secret values are visible, and
  (for parser test) a preview with ≥ 1 object appears.
- **Fail:** HTTP 5xx, blank output, a secret value visible in output, or an unhandled error
  chip with no JSON body.

---

## 1. SharePoint — health check

- **URL:** `/connectors/test-workbench`
- **Prerequisite config (real, optional):** `ECS_GRAPH_TENANT_ID`, `ECS_GRAPH_CLIENT_ID`,
  `ECS_GRAPH_CLIENT_SECRET`, `ECS_SHAREPOINT_SITE_HOSTNAME`/`ECS_GRAPH_SITE_ID`. Mock test
  needs **none**.
- **Frontend steps:** Select **SharePoint (Graph)** → click **Run health check**.
- **Expected result:** Status chip `configured` or `not_configured`; JSON with `status`,
  `configured`, `errors: []`, and a masked config block.
- **Fallback / error result:** If misconfigured, `status: not_configured` with `errors`
  listing missing keys — this is a valid, safe outcome (not a failure of the workbench).
- **Pass/fail:** Pass if 200 + JSON health object and no secret shown.

## 2. SharePoint — dry-run evidence pull

- **URL:** `/connectors/test-workbench`
- **Prerequisite config:** Same as above (optional for dry-run).
- **Frontend steps:** Select **SharePoint (Graph)** → click **Dry-run evidence pull**.
- **Expected result:** JSON `mode: "dry-run"`, `would_call: "fetch_drive_items"`,
  `configured: true|false`, masked config, and a note that **no network call was made**.
- **Fallback / error result:** `configured: false` if creds absent — still a successful
  dry-run (it reports what *would* run).
- **Pass/fail:** Pass if 200 + `mode: dry-run` + `would_call` present.

## 3. Teams — health check

- **URL:** `/connectors/test-workbench`
- **Prerequisite config (real, optional):** `ECS_GRAPH_*`, `ECS_TEAMS_TEAM_ID`,
  `ECS_TEAMS_CHANNEL_ID`.
- **Frontend steps:** Select **Microsoft Teams (Graph)** → **Run health check**.
- **Expected result:** JSON health object with `status` and masked config.
- **Fallback / error result:** `not_configured` + missing-key `errors`.
- **Pass/fail:** Pass if 200 + health JSON, no secret shown.

## 4. Outlook — health check

- **URL:** `/connectors/test-workbench`
- **Prerequisite config (real, optional):** `ECS_GRAPH_*`, `ECS_OUTLOOK_USER_ID`.
- **Frontend steps:** Select **Outlook (Graph)** → **Run health check**.
- **Expected result:** JSON health object with `status` and masked config.
- **Fallback / error result:** `not_configured` + missing-key `errors`.
- **Pass/fail:** Pass if 200 + health JSON.

## 5. Prisma Cloud — parser test

- **URL:** `/connectors/test-workbench`
- **Prerequisite config:** **None** for the mock parser test.
- **Frontend steps:** Select **Prisma Cloud** → click **Run parser test (mock)**.
- **Expected result:** `status: ok`, `method: fetch_alerts`,
  `evidence_objects_detected: 1`, and a JSON preview of the normalized alert.
- **Fallback / error result:** `status: parser_error` with a safe error type name if the
  parser path changes — investigate the adapter, not the workbench.
- **Pass/fail:** Pass if 200 + `ok: true` + preview with ≥ 1 object.

## 6. Jira — parser test

- **URL:** `/connectors/test-workbench`
- **Prerequisite config:** **None** for the mock parser test.
- **Frontend steps:** Select **Jira** → **Run parser test (mock)**.
- **Expected result:** `method: fetch_projects`, `evidence_objects_detected: 1`, preview
  of a normalized project.
- **Fallback / error result:** `parser_error` with safe error name.
- **Pass/fail:** Pass if 200 + `ok: true` + preview.

## 7. Confluence — parser test

- **URL:** `/connectors/test-workbench`
- **Prerequisite config:** **None** for the mock parser test.
- **Frontend steps:** Select **Confluence** → **Run parser test (mock)**.
- **Expected result:** `method: fetch_spaces`, `evidence_objects_detected: 1`, preview of
  a normalized space.
- **Fallback / error result:** `parser_error`.
- **Pass/fail:** Pass if 200 + `ok: true` + preview.

## 8. ServiceNow — parser test

- **URL:** `/connectors/test-workbench`
- **Prerequisite config:** **None** for the mock parser test.
- **Frontend steps:** Select **ServiceNow CMDB** → **Run parser test (mock)**.
- **Expected result:** `method: fetch_servers`, `evidence_objects_detected: 1`, preview of
  a normalized CI/server.
- **Fallback / error result:** `parser_error`.
- **Pass/fail:** Pass if 200 + `ok: true` + preview.

## 9. SonarQube — parser test

- **URL:** `/connectors/test-workbench`
- **Prerequisite config:** **None** for the mock parser test.
- **Frontend steps:** Select **SonarQube** → **Run parser test (mock)**.
- **Expected result:** `method: fetch_projects`, `evidence_objects_detected: 1`, preview of
  a normalized project.
- **Fallback / error result:** `parser_error`.
- **Pass/fail:** Pass if 200 + `ok: true` + preview.

## 10. Checkmarx — parser test

- **URL:** `/connectors/test-workbench`
- **Prerequisite config:** **None** for the mock parser test.
- **Frontend steps:** Select **Checkmarx** → **Run parser test (mock)**.
- **Expected result:** `method: fetch_scans`, `evidence_objects_detected: 1`, preview of a
  normalized scan.
- **Fallback / error result:** `parser_error`.
- **Pass/fail:** Pass if 200 + `ok: true` + preview.

## 11. Tripwire — parser test

- **URL:** `/connectors/test-workbench`
- **Prerequisite config:** **None** for the mock parser test.
- **Frontend steps:** Select **Tripwire** → **Run parser test (mock)**.
- **Expected result:** `method: fetch_policy_results`, `evidence_objects_detected: 1`,
  preview of a normalized policy result.
- **Fallback / error result:** `parser_error`.
- **Pass/fail:** Pass if 200 + `ok: true` + preview.

---

## 12. Switching from local mock to real UAT

The workbench's mock parser test proves the parser works with **no credentials**. To test
**live** connectivity against a bank UAT environment:

1. Populate real endpoints/credentials in `.env.uat` (never commit secrets) — see
   [`uat_ip_configuration_guide.md`](../operations/uat_ip_configuration_guide.md) and
   [`microsoft_graph_sharepoint_teams_uat_testing.md`](../graph-api/microsoft_graph_sharepoint_teams_uat_testing.md).
2. Validate config: `python scripts/validate_uat_config.py`.
3. Run **Config status** and **Health check** in the workbench — they should now show
   `configured: true`.
4. For live evidence collection (a real network call), use the standard evidence
   run/scheduler path with real credentials and a live transport — the workbench itself
   remains mock-only by design so it is always safe to click.

---

## 13. REST equivalents (for automation)

Every button maps to a read-only endpoint:

```bash
curl localhost:8000/api/connectors
curl localhost:8000/api/connectors/jira/config-status
curl -X POST localhost:8000/api/connectors/jira/health-check
curl -X POST localhost:8000/api/connectors/servicenow_cmdb/dry-run
curl -X POST localhost:8000/api/connectors/sharepoint_graph/parser-test
```
