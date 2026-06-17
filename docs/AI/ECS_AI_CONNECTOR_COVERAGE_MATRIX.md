# ECS AI Connector Coverage Matrix (Phase 6)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

**Key fact:** Connectors **ingest evidence**; they do not call LLMs. They feed the evidence pipeline
that *optionally* embeds content into pgvector via the local provider. So connectors are
**LLM-independent** and **air-gap compatible** as long as the target system is reachable on the
private network. None require internet to an AI provider.

---

## 1. Three connector layers in code

### A. Platform connectors (real integration layer) — `ecs_platform/connectors/factory.py:12-25`

`gitea, github, sonarqube, jenkins, jira, confluence, figma, servicenow, teams, sharepoint, prisma,
azure_devops` — configured in `config/integrations.yaml:6-185`, implemented as
`ecs_platform/connectors/*_connector.py`.

### B. Integrations Hub (demo dashboard) — `modules/operations/engines/integrations_module.py:7-212`

ServiceNow GRC, ServiceNow CMDB, SharePoint Evidence Library, Microsoft Teams Governance, Confluence
Governance Wiki, Jira Security Remediation, Prisma Cloud CSPM, Tripwire Enterprise, SonarQube
Enterprise, Checkmarx SAST, Splunk Enterprise SIEM, BMC Helix CMDB. (GitHub Advanced Security appears
only in `_CONNECTOR_CHALLENGES:243`.)

### C. Predefined-query scan connectors — `modules/operations/engines/query_connectors.py`

`gitleaks_connector.py`, `trivy_connector.py`, `sonarqube_connector.py`, `linux_connector.py`,
`postgresql_connector.py` (+ `connector_common.py`).

---

## 2. Requested connectors → presence → readiness

| Requested | Platform layer | Integrations Hub | Scan layer | Local/air-gap ready |
|---|---|---|---|---|
| Jira | ✅ `jira_connector.py` | ✅ | — | ✅ (on-prem Jira reachable) |
| Confluence | ✅ `confluence_connector.py` | ✅ | — | ✅ |
| ServiceNow | ✅ `servicenow_connector.py` | ✅ (×2) | — | ✅ |
| Teams | ✅ `teams_connector.py` | ✅ | — | ✅ (Teams is cloud SaaS — needs egress to MS; not AI-related) |
| SharePoint | ✅ `sharepoint_connector.py` | ✅ | — | ✅ (on-prem SharePoint ok) |
| GitHub | ✅ `github_connector.py` | (challenges only) | — | ✅ (GH Enterprise on-prem ok) |
| Gitea | ✅ `gitea_connector.py` | — | — | ✅ (self-hosted) |
| Azure DevOps | ✅ `azure_devops_connector.py` | — | — | ✅ (Server on-prem ok) |
| Jenkins | ✅ `jenkins_connector.py` | — | — | ✅ (self-hosted) |
| SonarQube | ✅ `sonarqube_connector.py` | ✅ | ✅ | ✅ (self-hosted) |
| Prisma Cloud | ✅ `prisma_connector.py` | ✅ | — | 🔶 (Prisma is SaaS; needs egress to Palo Alto — not AI-related) |

## 3. Additional connectors present (not in request)

- Platform: **Figma** (`figma_connector.py`).
- Hub: **Tripwire, Checkmarx, Splunk SIEM, BMC Helix CMDB**.
- Scan: **Gitleaks, Trivy, Linux, PostgreSQL**.

## 4. Connector → AI pipeline relationship

```
Connector (ingest)  ──>  Evidence pipeline  ──>  (optional) provider.embed()  ──>  pgvector (local)
ecs_platform/connectors/*        ecs_platform/ingestion.py:203-231     provider.py:195-206   pgvector_store.py
```

The embedding step uses the **local provider by default**; if the provider is unconfigured, ingestion
still stores evidence (vectorization is the only part that needs the model). **No connector calls a
cloud AI service.**

## 5. Readiness summary

| Status | Connectors |
|---|---|
| Local/self-hosted ready | Jira, Confluence, ServiceNow, SharePoint, GitHub(EE), Gitea, Azure DevOps(Server), Jenkins, SonarQube, Gitleaks, Trivy, Linux, PostgreSQL, Tripwire, Checkmarx, Splunk, BMC Helix |
| SaaS egress required (non-AI) | Teams, Prisma Cloud, Figma — note: these need network egress to their vendor, not to any AI provider; replace/disable for fully air-gapped deployments |

**All requested connectors exist** (GitHub/Gitleaks/Trivy with the location notes above) and are
**compatible with local-LLM/air-gapped ECS**, because connectors are independent of the AI provider.
