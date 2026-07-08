# ECS Predefined Query — Framework & Technology Coverage Matrix

Derived from the live control catalog (187 controls; see
[PREDEFINED_QUERY_INVENTORY.md](PREDEFINED_QUERY_INVENTORY.md)). Status legend:

- **Covered** — predefined queries exist AND an execution connector exists.
- **Partial** — some queries/controls exist but coverage is thin or connector is generic.
- **Missing** — no predefined queries yet (a genuine gap).
- **N/A** — not applicable to ECS predefined-query execution.
- **Needs Docker target** — connector exists; add/enable a local demo container to test.
- **Needs UAT credentials** — connector exists; requires real endpoint + secret to run.

---

## 1. Technology coverage

| Technology | Status | Queries | Connector | Local Docker target | Notes |
|---|---|---:|---|---|---|
| Linux | Covered | 15 | LinuxConnector | `ubuntu-demo` | OS baseline |
| Red Hat 8 | Covered | 8 | LinuxConnector | `rhel8-demo` (`infra-demo`) | UBI8 image |
| Red Hat 9 | Covered | 8 | LinuxConnector | `rhel9-demo` (`infra-demo`) | UBI9 image |
| Windows | Partial | 3 | (generic SSH — not implemented) | Needs UAT credentials | Queries exist (Excel); no local target / WinRM connector |
| Nginx | Covered | 9 | LinuxConnector | `nginx-demo` (`infra-demo`) | + `demo-data/nginx` |
| Apache HTTPD | Covered | 8 | LinuxConnector | `apache-demo` (`infra-demo-extended`) | |
| Tomcat | Covered | 9 | LinuxConnector | `tomcat-demo` (`infra-demo-extended`) | |
| WebLogic | Missing | 0 | — | — | No connector/target — recommend (see §4) |
| JBoss/WildFly | Missing | 0 | — | — | No connector/target — recommend (see §4) |
| PostgreSQL | Covered | 11 | PostgreSQLConnector | `postgres-demo` | |
| Oracle | Covered | 12 | OracleConnector | `oracle-demo` (`oracle-demo`, heavy) | |
| MySQL / Aurora | Covered | 11 | MySQLConnector | `mysql-demo` (`db-targets`) | |
| SQL Server | Covered | 10 | SQLServerConnector | `sqlserver-demo` (heavy) | |
| MongoDB | Covered | 8 | MongoDBConnector | `mongodb-demo` (`db-demo-extended`) | |
| YugabyteDB | Covered | 9 | YugabyteConnector | `yugabyte` (`db-targets`) | |
| Redis | Covered | 8 | RedisConnector | `redis` (default) | |
| Aerospike | Covered | 20 | AerospikeConnector | `aerospike` (`aerospike`/`demo`) | |
| Kafka | Missing | 0 | — | Needs Docker target | No connector/target — recommend (see §4) |
| RabbitMQ | Missing | 0 | — | Needs Docker target | No connector/target — recommend (see §4) |
| Kubernetes | Covered | 10 | KubernetesConnector (kubectl) | Needs UAT credentials (kubeconfig) | No heavy local cluster by design |
| OpenShift | Covered | 10 | OpenShiftConnector (oc) | Needs UAT credentials (kubeconfig) | |
| Jenkins | Partial | (source connector) | ecs_platform connector | `jenkins` (`sources`) | Evidence via connector framework, not predefined-query catalog |
| SonarQube | Covered | 1 | SonarQubeConnector | `sonarqube-demo` (`demo-connectors`) | AppSec; more checks available via REST |
| Checkmarx | Partial | (integration adapter) | checkmarx adapter | Needs UAT credentials | Adapter-based (not in predefined-query catalog) |
| Prisma Cloud | Partial | (integration adapter) | prisma_cloud adapter | Needs UAT credentials | Adapter-based |
| Tripwire | Partial | (integration adapter) | tripwire adapter | Needs UAT credentials | Adapter-based |
| ServiceNow CMDB | Partial | (integration adapter) | servicenow_cmdb adapter | Needs UAT credentials | Adapter-based |
| Jira | Partial | (integration adapter) | jira adapter | Needs UAT credentials | Adapter-based |
| Confluence | Partial | (integration adapter) | confluence adapter | Needs UAT credentials | Adapter-based |
| SharePoint | Partial | (integration adapter) | sharepoint_graph adapter | Needs UAT credentials | Graph OAuth |
| Teams | Partial | (integration adapter) | teams_graph adapter | Needs UAT credentials | Graph OAuth |
| Outlook | Partial | (integration adapter) | outlook_graph adapter | Needs UAT credentials | Graph OAuth |
| AWS | Partial | (integration adapter) | aws_connector | Needs UAT credentials | Cloud posture adapter |
| Azure | Partial | (integration adapter) | azure_connector | Needs UAT credentials | Cloud posture adapter |
| GCP | Partial | (integration adapter) | gcp_connector | Needs UAT credentials | Cloud posture adapter |
| Nessus | Partial | (integration adapter) | nessus adapter | Needs UAT credentials | VAPT scanner adapter |
| Qualys | Partial | (integration adapter) | qualys adapter | Needs UAT credentials | VAPT scanner adapter |
| Trivy | Covered | 1 | TrivyConnector | (image scan, local) | Supply-chain |
| GitLeaks | Covered | 1 | GitLeaksConnector | (scan path, local) | Secret scanning |

> **Adapter-based vs predefined-query:** ITSM/GRC/cloud/scanner systems
> (ServiceNow, Jira, Confluence, SharePoint/Teams/Outlook, AWS/Azure/GCP,
> Nessus/Qualys, Checkmarx, Prisma, Tripwire) are integrated through the
> **enterprise integration adapters** (`modules/operations/integrations/`), which
> already externalize their config (see the Connector Configuration Guide). They
> are marked *Partial* here because they are not part of the shell/SQL
> predefined-query catalog, not because they are unimplemented.

---

## 2. Framework coverage (from catalog `frameworks`)

| Framework | Status | Present on technologies |
|---|---|---|
| PCI DSS | Covered | Linux, NGINX, Tomcat, PostgreSQL, Oracle, Aurora MySQL, Windows |
| DPSC | Covered | Linux, NGINX, PostgreSQL, Oracle, Aurora MySQL, GitLeaks, Windows |
| C-SITE (CSITE) | Covered | YugabyteDB, Windows, (Excel-mapped controls) |
| ISO27001 | Covered | Most technologies (DB, middleware, OS, container) |
| ITPP | Covered | Linux, (Excel-mapped) |
| DB baseline | Covered | PostgreSQL, Oracle, Aurora MySQL, SQL Server, MongoDB, YugabyteDB, Aerospike |
| OS baseline | Covered | Linux, RHEL 8, RHEL 9, Windows |
| Middleware baseline | Covered | NGINX, Apache, Tomcat, Redis |
| Nginx baseline | Covered | NGINX (via Middleware Baselining + NGX-*) |
| Tomcat baseline | Covered | Tomcat (via Middleware Baselining + TCX-*) |
| VAPT | Partial | Linux, Windows + Nessus/Qualys adapters (Needs UAT credentials) |
| RBI Cyber Security | Covered | Broad (DB/middleware/OS/container) |
| MBSS | Partial | Windows |
| CIS | Partial | Implicitly via OS/DB/middleware baselines; no explicit CIS-tagged control set |
| DR | Partial | ITDRM-tagged controls (PostgreSQL) + backup/archive checks; not a dedicated DR framework tag |
| Backup | Partial | DB archive/backup checks (PostgreSQL archive mode, etc.) |
| Capacity | Partial | Disk/CPU/memory (Linux), DB sizing — not a dedicated framework tag |
| Availability | Partial | Cluster/replication checks (K8s/OpenShift/DB) |
| Change management | Needs UAT credentials | Jira/ServiceNow adapters (evidence, not shell/SQL queries) |
| Incident management | Needs UAT credentials | ServiceNow adapter |
| Access control | Covered | Role/privilege/RBAC checks across DB/OS/container |
| Encryption at rest | Partial | DB TDE/wallet checks (Oracle), storage flags |
| Encryption in transit | Covered | TLS/SSL checks across NGINX/Tomcat/DB |

---

## 3. Framework × Technology matrix (catalog-derived, condensed)

Legend: ● Covered · ◐ Partial · — none. (Only the shell/SQL predefined-query
catalog is counted here; adapter-based frameworks are noted in §1–§2.)

| Framework \ Tech | Linux | RHEL8/9 | NGINX | Apache | Tomcat | PG | Oracle | MySQL | MSSQL | Mongo | Yugabyte | Redis | Aerospike | K8s | OpenShift |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| OS Baselining | ● | ● | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Middleware Baselining | — | — | ● | ● | ● | — | — | — | — | — | — | ● | — | — | — |
| DB Baselining | — | — | — | — | — | ● | ● | ● | ● | ● | ● | — | ● | — | — |
| Container Platform | — | — | — | — | — | — | — | — | — | — | — | — | — | ● | ● |
| PCI DSS | ● | — | ● | — | ● | ● | ● | ● | — | — | — | — | — | — | — |
| DPSC | ● | — | ● | — | — | ● | ● | ● | — | — | — | — | — | — | — |
| ISO27001 | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| RBI Cyber Security | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| Encryption in transit | ● | — | ● | ◐ | ● | ● | ● | ● | ◐ | — | — | ◐ | ◐ | — | ● |
| Access control | ● | ● | — | — | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |

---

## 4. Genuine gaps & recommendations (NOT implemented in this pass)

These are real gaps; they are **documented, not implemented**, because closing
them requires new execution connectors and/or Docker targets (engine work that is
out of scope for an additive catalog pass):

| Gap | Why deferred | Recommended approach |
|---|---|---|
| **Kafka** predefined queries | No connector, no local target | Add `KafkaConnector` reusing the docker-exec `LinuxConnector` pattern (`kafka-topics.sh`/`kafka-configs.sh`), a `kafka` demo service behind an `extended` profile, and KFK-* catalog entries. |
| **RabbitMQ** predefined queries | No connector, no local target | Add via `rabbitmqctl` / management REST on the same pattern; `rabbitmq` demo service behind `extended`; RMQ-* entries. |
| **WebLogic / JBoss/WildFly** | No connector, no target, licensed images | Config-file/WLST or JMX reads; likely UAT-only (no free local image). |
| **Windows** deeper coverage | Only 3 Excel controls; SSH connector is a stub | Implement a WinRM/PowerShell connector; run against a UAT Windows host (no local target). |
| **Explicit CIS-tagged** control set | Coverage is implicit via OS/DB/middleware baselines | Tag existing baseline controls with a `CIS` framework label (metadata-only) if a CIS report is required. |
| Dedicated **DR / Backup / Capacity / Availability** framework tags | Covered functionally but not as first-class framework tags | Add framework labels to the relevant existing controls (metadata-only). |

Adding any of the above should follow the existing convention: extend
`supplementary_query_catalog.py` + a connector + `TECHNOLOGY_RULES` +
`_IMPLEMENTED_CONNECTOR_TECH` + a `predefined_query_targets` block — never a
parallel catalog.
