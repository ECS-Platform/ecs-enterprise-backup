# ECS Agent Architecture Guide

## 1. Purpose

Defines the hybrid ECS evidence collection architecture using API
connectors where possible and agents only where required.

## 2. Design Principles

-   Prefer APIs over agents.
-   Use agents only for private networks, databases, OS and middleware.
-   Read-only evidence collection.
-   Upload through ECS APIs only.

## 3. High-Level Architecture

``` mermaid
flowchart TD
ECS[ECS on GKE]
ECS-->API[API Connectors]
ECS-->DB[DB Agent]
ECS-->AWS[AWS Agent]
ECS-->GCP[GCP Agent]
ECS-->OS[OS Agent]
API-->M365[SharePoint/Teams/Outlook]
API-->Jira[Jira/Confluence]
API-->SNOW[ServiceNow]
```

## 4. Collection Modes

  Mode         Agent
  ------------ ------------
  API          No
  Cloud API    Usually No
  Database     Yes
  OS           Yes
  Middleware   Yes
  Kubernetes   Optional

## 5. No-Agent Systems

Microsoft 365, Jira, Confluence, ServiceNow, Prisma, SonarQube,
Checkmarx, GitHub, Jenkins, Azure DevOps, AWS APIs, GCP APIs.

## 6. Agent-Based Systems

Private databases, Linux, Windows, Nginx, middleware, air-gapped
systems, jump-server environments.

## 7. GCP

ECS runs on GKE with Scheduler, Evidence Repository, Audit Intelligence,
Connector Framework, Benchmark Workbench and Prompt Workbench.

## 8. AWS

Use AWS Evidence Agent for EC2, Aurora, middleware and upload evidence
to ECS.

## 9. Mobile Banking

Use GCP APIs, Kubernetes APIs and DB Agent where SQL evidence is
required.

## 10. Payments

AWS → AWS Agent; GCP → GCP Agent; DB → DB Agent; SaaS → API.

## 11. DB Agent

Loads predefined queries, executes read-only SQL, hashes evidence and
uploads to ECS.

## 12. OS/Middleware Agent

Collects OS version, patching, services, firewall, TLS, Nginx, Tomcat,
Kafka and middleware configuration.

## 13. Kubernetes Agent

Collects cluster version, nodes, deployments, pods, RBAC and network
policies.

## 14. Evidence Flow

``` mermaid
flowchart LR
Agent-->Normalize-->Hash-->Upload-->Repository-->Dashboard
```

## 15. Security

Least privilege, secrets manager, TLS, audit logging, retries and
SHA-256 verification.

## 16. Decision Matrix

API available = API connector. Private infrastructure = Agent.

## 17. Environments

LOCAL (Mock), DEV (API+DB Agent), SIT (Representative), UAT (Full), PROD
(Hardened), DR (Mirror).

## 18. Monitoring

Heartbeat, execution time, upload success, evidence count, failures.

## 19. Future Enhancements

Agent Registry, Health Dashboard, Policy Engine, Drift Detection, Signed
Evidence.

## 20. Summary

Adopt a hybrid API + Agent architecture for secure, scalable enterprise
evidence collection.
