# ECS Predefined Query Inventory

> **Auto-generated** from the live control catalog (Excel control library +
> `modules/operations/engines/supplementary_query_catalog.py`) via
> `scripts/run_predefined_query_tests.py inventory`. Do not hand-edit; regenerate.
>
> Generated: 2026-07-08

## Summary

- **Total controls:** 208
- **Executable (connector + driver/target available in a configured env):** 141
- **Technologies:** 21
- **Frameworks:** 16

### Controls by technology

| Technology | Controls |
|---|---:|
| Aerospike | 20 |
| Apache HTTPD | 8 |
| Aurora MySQL | 15 |
| GitLeaks | 1 |
| Kubernetes | 10 |
| Linux | 15 |
| MongoDB | 10 |
| NGINX | 9 |
| OpenShift | 10 |
| Oracle | 16 |
| PostgreSQL | 16 |
| Red Hat Enterprise Linux 8.x | 8 |
| Red Hat Enterprise Linux 9.x | 8 |
| Redis | 8 |
| SQL Server | 13 |
| SonarQube | 1 |
| Tomcat | 9 |
| Trivy | 1 |
| Unknown | 15 |
| Windows | 3 |
| YugabyteDB | 12 |

## Query catalog

Columns: **Query ID · Name · Framework(s) · Technology · Exec type ·
Evidence type · Status · Executable**. Query text, allow-list gating, parser
and validation live in the engine and per-technology connectors.

| Query ID | Name | Framework(s) | Technology | Exec type | Evidence type | Status | Executable |
|---|---|---|---|---|---|---|---|
| ASX-001 | Aerospike Server Version | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-002 | Aerospike Cluster Status | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-003 | Aerospike Namespace List | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-004 | Aerospike Namespace Config | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-005 | Aerospike Security Config | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-006 | Aerospike User/Role List | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-007 | Aerospike TLS Config | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-008 | Aerospike Service Ports | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-009 | Aerospike Storage Engine Config | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-010 | Aerospike Backup Policy | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-011 | Aerospike XDR Config | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-012 | Aerospike Audit Logging | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-013 | Aerospike Memory Usage | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-014 | Aerospike Index Usage | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-015 | Aerospike Cluster Node Count | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-016 | Aerospike Namespace Replication Factor | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-017 | Aerospike Strong Consistency | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-018 | Aerospike Expiration/TTL Config | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-019 | Aerospike Secondary Index List | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| ASX-020 | Aerospike Latency / Slow Query | DB Baselining, ISO27001, RBI Cyber Security | Aerospike | Shell command | Aerospike asinfo/asadm output | Ready | yes |
| APX-001 | Apache Version | Middleware Baselining, ISO27001, RBI Cyber Security | Apache HTTPD | Shell command | Apache HTTPD command output | Ready | yes |
| APX-002 | Apache Config Test | Middleware Baselining, ISO27001, RBI Cyber Security | Apache HTTPD | Shell command | Apache HTTPD command output | Ready | yes |
| APX-003 | Apache Loaded Modules | Middleware Baselining, ISO27001, RBI Cyber Security | Apache HTTPD | Shell command | Apache HTTPD command output | Ready | yes |
| APX-004 | Apache ServerTokens | Middleware Baselining, ISO27001, RBI Cyber Security | Apache HTTPD | Shell command | Apache HTTPD command output | Ready | yes |
| APX-005 | Apache ServerSignature | Middleware Baselining, ISO27001, RBI Cyber Security | Apache HTTPD | Shell command | Apache HTTPD command output | Ready | yes |
| APX-006 | Apache SSL Protocols | Middleware Baselining, ISO27001, RBI Cyber Security | Apache HTTPD | Shell command | Apache HTTPD command output | Ready | yes |
| APX-007 | Apache Access Log Config | Middleware Baselining, ISO27001, RBI Cyber Security | Apache HTTPD | Shell command | Apache HTTPD command output | Ready | yes |
| APX-008 | Apache Error Log Config | Middleware Baselining, ISO27001, RBI Cyber Security | Apache HTTPD | Shell command | Apache HTTPD command output | Ready | yes |
| DB-007 | SSL Enabled | DB Baselining, PCI DSS, DPSC | Aurora MySQL | SQL | SQL Output | Configuration Required | no |
| MYX-001 | Aurora MySQL SSL Status | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-002 | Aurora MySQL Secure Transport | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-003 | Aurora MySQL Binary Logging | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-004 | Aurora MySQL Audit Variables | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-005 | Aurora MySQL Users | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-006 | Aurora MySQL Version | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-007 | Aurora MySQL Databases | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-008 | Aurora MySQL Process List | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-009 | Aurora MySQL Grants Summary | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-010 | Aurora MySQL TLS Config | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-011 | Aurora MySQL Connection Limits | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-012 | Aurora MySQL Long Running Queries | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-013 | Aurora MySQL Failed Connections | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| MYX-014 | Aurora MySQL Uptime | DB Baselining, ISO27001, RBI Cyber Security | Aurora MySQL | SQL | Database configuration query output | Ready | yes |
| APP-002 | Secrets Scanning | AppSec, ASST, DPSC | GitLeaks | CLI scanner | Scan Report | Ready | yes |
| K8X-001 | Kubernetes Version | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-002 | Kubernetes Nodes | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-003 | Kubernetes Namespaces | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-004 | Kubernetes Cluster Roles | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-005 | Kubernetes Cluster Role Bindings | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-006 | Kubernetes Pod Security | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-007 | Kubernetes Network Policies | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-008 | Kubernetes Secrets Inventory | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-009 | Kubernetes Service Accounts | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| K8X-010 | Kubernetes PSP/PSA Labels | Container Platform Baselining, ISO27001, RBI Cyber Security | Kubernetes | CLI (kubectl/oc) | Kubernetes kubectl output | Ready | yes |
| ITPP-002 | Capacity Management | ITPP | Linux | Shell command | Command Output | Configuration Required | no |
| ITPP-003 | Memory Utilization | ITPP | Linux | Shell command | Command Output | Configuration Required | no |
| LNX-001 | Linux OS Release | OS Baselining, ISO27001, RBI Cyber Security | Linux | Shell command | OS configuration command output | Ready | yes |
| LNX-002 | Linux Kernel Version | OS Baselining, ISO27001, RBI Cyber Security | Linux | Shell command | OS configuration command output | Ready | yes |
| LNX-003 | Linux Running Services | OS Baselining, ISO27001, RBI Cyber Security | Linux | Shell command | OS configuration command output | Ready | yes |
| LNX-004 | Linux Firewall Status | OS Baselining, ISO27001, RBI Cyber Security | Linux | Shell command | OS configuration command output | Ready | yes |
| LNX-005 | Linux SSH Root Login Setting | OS Baselining, ISO27001, RBI Cyber Security | Linux | Shell command | OS configuration command output | Ready | yes |
| LNX-006 | Linux Password Authentication Setting | OS Baselining, ISO27001, RBI Cyber Security | Linux | Shell command | OS configuration command output | Ready | yes |
| LNX-007 | Linux Sudoers Configuration | OS Baselining, ISO27001, RBI Cyber Security | Linux | Shell command | OS configuration command output | Ready | yes |
| LNX-008 | Linux Local Users | OS Baselining, ISO27001, RBI Cyber Security | Linux | Shell command | OS configuration command output | Ready | yes |
| OS-001 | Patch Compliance | OS Baselining, PCI DSS, DPSC, VAPT | Linux | Shell command | Command Output | Ready | yes |
| OS-002 | SSH Hardening | OS Baselining, PCI DSS | Linux | Shell command | Configuration File | Ready | yes |
| OS-003 | NTP Synchronization | OS Baselining | Linux | Shell command | Command Output | Configuration Required | no |
| OS-004 | User Account Review | OS Baselining, PCI DSS | Linux | Shell command | Configuration File | Configuration Required | no |
| OS-005 | Service Hardening | OS Baselining | Linux | Shell command | Command Output | Configuration Required | no |
| MGX-001 | MongoDB Build Info | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-002 | MongoDB Server Status | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-003 | MongoDB Auth Enabled | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-004 | MongoDB TLS Config | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-005 | MongoDB Users | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-006 | MongoDB Roles | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-007 | MongoDB Databases | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-008 | MongoDB Audit Config | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-009 | MongoDB Replication Status | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MGX-010 | MongoDB Current Operations | DB Baselining, ISO27001, RBI Cyber Security | MongoDB | Mongo command | MongoDB command output | Dependency Missing | no |
| MW-001 | TLS Configuration | Middleware Baselining, PCI DSS, DPSC | NGINX | Shell command | Configuration Export | Configuration Required | no |
| NGX-001 | NGINX Version | Middleware Baselining, ISO27001, RBI Cyber Security | NGINX | Shell command | Middleware command output | Ready | yes |
| NGX-002 | NGINX Config Test | Middleware Baselining, ISO27001, RBI Cyber Security | NGINX | Shell command | Middleware command output | Ready | yes |
| NGX-003 | NGINX TLS Protocol Configuration | Middleware Baselining, ISO27001, RBI Cyber Security | NGINX | Shell command | Middleware command output | Ready | yes |
| NGX-004 | NGINX TLS Cipher Configuration | Middleware Baselining, ISO27001, RBI Cyber Security | NGINX | Shell command | Middleware command output | Ready | yes |
| NGX-005 | NGINX Server Tokens Disabled | Middleware Baselining, ISO27001, RBI Cyber Security | NGINX | Shell command | Middleware command output | Ready | yes |
| NGX-006 | NGINX Access Log Configuration | Middleware Baselining, ISO27001, RBI Cyber Security | NGINX | Shell command | Middleware command output | Ready | yes |
| NGX-007 | NGINX Error Log Configuration | Middleware Baselining, ISO27001, RBI Cyber Security | NGINX | Shell command | Middleware command output | Ready | yes |
| NGX-008 | NGINX Enabled Sites | Middleware Baselining, ISO27001, RBI Cyber Security | NGINX | Shell command | Middleware command output | Ready | yes |
| OCX-001 | OpenShift Version | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-002 | OpenShift Cluster Operators | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-003 | OpenShift Nodes | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-004 | OpenShift Projects | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-005 | OpenShift Cluster Roles | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-006 | OpenShift Role Bindings | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-007 | OpenShift SCC | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-008 | OpenShift OAuth Config | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-009 | OpenShift Routes | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| OCX-010 | OpenShift Image Policies | Container Platform Baselining, ISO27001, RBI Cyber Security | OpenShift | CLI (kubectl/oc) | OpenShift oc output | Ready | yes |
| DB-004 | Encryption At Rest | DB Baselining, PCI DSS, DPSC | Oracle | SQL | SQL Output | Configuration Required | no |
| ORX-001 | Oracle Version | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-002 | Oracle Database Open Mode | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-003 | Oracle Encryption Wallet Status | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-004 | Oracle Audit Trail Setting | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-005 | Oracle Failed Login Profile Settings | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-006 | Oracle Privileged Users | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-007 | Oracle Roles Granted To Users | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-008 | Oracle Tablespace Usage | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-009 | Oracle Datafile Encryption Status | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-010 | Oracle Active Sessions | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-011 | Oracle Connection/Resource Limits | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-012 | Oracle Instance Uptime | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-013 | Oracle Long Running Sessions | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| ORX-014 | Oracle Schema Object Inventory | DB Baselining, ISO27001, RBI Cyber Security | Oracle | SQL | Database configuration query output | Dependency Missing | no |
| PCI-003 | Privileged Access Review | PCI DSS, DPSC, DB Baselining | Oracle | SQL | SQL Output | Configuration Required | no |
| DB-001 | SSL Enabled | DB Baselining, PCI DSS, DPSC | PostgreSQL | SQL | SQL Output | Ready | yes |
| DB-002 | Password Policy | DB Baselining, PCI DSS | PostgreSQL | SQL | SQL Output | Ready | yes |
| DB-003 | Replication Health | DB Baselining, ITDRM | PostgreSQL | SQL | SQL Output | Ready | yes |
| PGX-001 | PostgreSQL SSL Enabled | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-002 | PostgreSQL Password Encryption | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-003 | PostgreSQL Replication Status | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-004 | PostgreSQL User Privileges | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-005 | PostgreSQL Database Sizes | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-006 | PostgreSQL Active Sessions | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-007 | PostgreSQL Installed Extensions | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-008 | PostgreSQL Audit Extension Check | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-009 | PostgreSQL Connection Limits | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-010 | PostgreSQL Long Running Queries | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-011 | PostgreSQL Database Uptime | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-012 | PostgreSQL Schema Inventory | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| PGX-013 | PostgreSQL Security Parameters | DB Baselining, ISO27001, RBI Cyber Security | PostgreSQL | SQL | Database configuration query output | Ready | yes |
| RH8-001 | RHEL 8 Version Check | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 8.x | Shell command | OS configuration command output | Ready | yes |
| RH8-002 | RHEL 8 Crypto Policy | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 8.x | Shell command | OS configuration command output | Ready | yes |
| RH8-003 | RHEL 8 SELinux Status | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 8.x | Shell command | OS configuration command output | Ready | yes |
| RH8-004 | RHEL 8 Firewalld Status | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 8.x | Shell command | OS configuration command output | Ready | yes |
| RH8-005 | RHEL 8 Auditd Status | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 8.x | Shell command | OS configuration command output | Ready | yes |
| RH8-006 | RHEL 8 SSH PermitRootLogin | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 8.x | Shell command | OS configuration command output | Ready | yes |
| RH8-007 | RHEL 8 Password Authentication | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 8.x | Shell command | OS configuration command output | Ready | yes |
| RH8-008 | RHEL 8 Installed Security Updates | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 8.x | Shell command | OS configuration command output | Ready | yes |
| RH9-001 | RHEL 9 Version Check | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 9.x | Shell command | OS configuration command output | Ready | yes |
| RH9-002 | RHEL 9 Crypto Policy | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 9.x | Shell command | OS configuration command output | Ready | yes |
| RH9-003 | RHEL 9 SELinux Status | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 9.x | Shell command | OS configuration command output | Ready | yes |
| RH9-004 | RHEL 9 Firewalld Status | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 9.x | Shell command | OS configuration command output | Ready | yes |
| RH9-005 | RHEL 9 Auditd Status | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 9.x | Shell command | OS configuration command output | Ready | yes |
| RH9-006 | RHEL 9 SSH PermitRootLogin | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 9.x | Shell command | OS configuration command output | Ready | yes |
| RH9-007 | RHEL 9 Password Authentication | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 9.x | Shell command | OS configuration command output | Ready | yes |
| RH9-008 | RHEL 9 FIPS Mode | OS Baselining, ISO27001, RBI Cyber Security | Red Hat Enterprise Linux 9.x | Shell command | OS configuration command output | Ready | yes |
| RDX-001 | Redis Server Info | Middleware Baselining, ISO27001, RBI Cyber Security | Redis | Shell command | Redis configuration command output | Ready | yes |
| RDX-002 | Redis Persistence Config | Middleware Baselining, ISO27001, RBI Cyber Security | Redis | Shell command | Redis configuration command output | Ready | yes |
| RDX-003 | Redis AOF Enabled | Middleware Baselining, ISO27001, RBI Cyber Security | Redis | Shell command | Redis configuration command output | Ready | yes |
| RDX-004 | Redis Requirepass Set | Middleware Baselining, ISO27001, RBI Cyber Security | Redis | Shell command | Redis configuration command output | Ready | yes |
| RDX-005 | Redis Protected Mode | Middleware Baselining, ISO27001, RBI Cyber Security | Redis | Shell command | Redis configuration command output | Ready | yes |
| RDX-006 | Redis Bind Address | Middleware Baselining, ISO27001, RBI Cyber Security | Redis | Shell command | Redis configuration command output | Ready | yes |
| RDX-007 | Redis TLS Port | Middleware Baselining, ISO27001, RBI Cyber Security | Redis | Shell command | Redis configuration command output | Ready | yes |
| RDX-008 | Redis Maxmemory Policy | Middleware Baselining, ISO27001, RBI Cyber Security | Redis | Shell command | Redis configuration command output | Ready | yes |
| MSX-001 | SQL Server Version | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-002 | SQL Server Edition/Level | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-003 | SQL Server Authentication Mode | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-004 | SQL Server Logins | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-005 | SQL Server sysadmin Members | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-006 | SQL Server Databases | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-007 | SQL Server TDE Status | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-008 | SQL Server Force Encryption | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-009 | SQL Server Audit Specifications | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-010 | SQL Server Failed Login Auditing | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-011 | SQL Server Connection Limit | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-012 | SQL Server Long Running Requests | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| MSX-013 | SQL Server Uptime | DB Baselining, ISO27001, RBI Cyber Security | SQL Server | SQL | SQL Server query output | Dependency Missing | no |
| APP-001 | SAST Scan | AppSec, ASST, DPSC | SonarQube | REST API | API Output | Ready | yes |
| MW-003 | Admin Account Review | Middleware Baselining, PCI DSS | Tomcat | Shell command | Configuration File | Configuration Required | no |
| TCX-001 | Tomcat Version | Middleware Baselining, ISO27001, RBI Cyber Security | Tomcat | Shell command | Tomcat command/config output | Ready | yes |
| TCX-002 | Tomcat Process Running | Middleware Baselining, ISO27001, RBI Cyber Security | Tomcat | Shell command | Tomcat command/config output | Ready | yes |
| TCX-003 | Tomcat server.xml Present | Middleware Baselining, ISO27001, RBI Cyber Security | Tomcat | Shell command | Tomcat command/config output | Ready | yes |
| TCX-004 | Tomcat HTTP Connectors | Middleware Baselining, ISO27001, RBI Cyber Security | Tomcat | Shell command | Tomcat command/config output | Ready | yes |
| TCX-005 | Tomcat Manager App Present | Middleware Baselining, ISO27001, RBI Cyber Security | Tomcat | Shell command | Tomcat command/config output | Ready | yes |
| TCX-006 | Tomcat Users Config | Middleware Baselining, ISO27001, RBI Cyber Security | Tomcat | Shell command | Tomcat command/config output | Ready | yes |
| TCX-007 | Tomcat Shutdown Port | Middleware Baselining, ISO27001, RBI Cyber Security | Tomcat | Shell command | Tomcat command/config output | Ready | yes |
| TCX-008 | Tomcat Access Valve Logging | Middleware Baselining, ISO27001, RBI Cyber Security | Tomcat | Shell command | Tomcat command/config output | Ready | yes |
| APP-004 | Container Security Scan | AppSec, ASST | Trivy | CLI scanner | Scan Report | Configuration Required | no |
| AI-001 | Model Approval | AI SDLC | Unknown | Shell command | SQL Output | Unsupported Technology | no |
| AI-002 | Prompt Approval | AI SDLC | Unknown | Shell command | SQL Output | Unsupported Technology | no |
| AI-003 | Hallucination Testing | AI SDLC | Unknown | Shell command | SQL Output | Unsupported Technology | no |
| APP-003 | Dependency Scanning | AppSec, ASST | Unknown | Shell command | Scan Report | Unsupported Technology | no |
| DB-005 | Audit Logging | DB Baselining, PCI DSS, CSITE | Unknown | Shell command | SQL Output | Unsupported Technology | no |
| DPSC-001 | API Authentication | DPSC, AppSec | Unknown | Shell command | API Output | Unsupported Technology | no |
| DPSC-002 | API Rate Limiting | DPSC, AppSec | Unknown | Shell command | API Output | Unsupported Technology | no |
| ITPP-001 | Backup Success | ITPP, ITDRM | Unknown | Shell command | Log Output | Unsupported Technology | no |
| ITPP-004 | CPU Utilization | ITPP | Unknown | Shell command | Command Output | Unsupported Technology | no |
| MW-002 | Certificate Expiry | Middleware Baselining, PCI DSS, DPSC | Unknown | Shell command | Certificate Output | Unsupported Technology | no |
| PCI-002 | Audit Logging Validation | PCI DSS, CSITE | Unknown | Shell command | Search Output | Unsupported Technology | no |
| PCI-004 | Encryption In Transit | PCI DSS, DPSC, Middleware Baselining | Unknown | Shell command | Certificate Output | Unsupported Technology | no |
| VAPT-001 | Vulnerability Scan | VAPT, PCI DSS, DPSC | Unknown | Shell command | API Output | Unsupported Technology | no |
| VAPT-002 | Critical Vulnerability Closure | VAPT, PCI DSS | Unknown | Shell command | API Output | Unsupported Technology | no |
| VAPT-003 | DAST Findings | VAPT, AppSec | Unknown | Shell command | API Output | Unsupported Technology | no |
| OS-006 | Patch Compliance | OS Baselining, PCI DSS, DPSC, VAPT | Windows | Shell command | PowerShell Output | Connector Missing | no |
| OS-007 | Antivirus Status | OS Baselining, CSITE | Windows | Shell command | PowerShell Output | Connector Missing | no |
| PCI-001 | MFA/User Review | PCI DSS, DPSC, MBSS | Windows | Shell command | PowerShell Output | Connector Missing | no |
| DB-006 | Cluster Health | DB Baselining, CSITE | YugabyteDB | SQL | SQL Output | Configuration Required | no |
| YBX-001 | YugabyteDB Cluster Servers | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-002 | YugabyteDB Version | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-003 | YugabyteDB Active Sessions | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-004 | YugabyteDB User Privileges | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-005 | YugabyteDB Database Sizes | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-006 | YugabyteDB Table List | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-007 | YugabyteDB Extensions | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-008 | YugabyteDB SSL Check | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-009 | YugabyteDB Connection Limits | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-010 | YugabyteDB Long Running Queries | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
| YBX-011 | YugabyteDB Security Parameters | DB Baselining, ISO27001, RBI Cyber Security | YugabyteDB | SQL | Database configuration query output | Ready | yes |
