# ECS Glossary

Abbreviations and acronyms used across the ECS (Evidence & Compliance System)
codebase and documentation. Scope is **ECS-domain and compliance-domain** terms —
generic web/IT abbreviations (HTTP, JSON, API, SQL, URL, ID, HTML, CSV, YAML, …)
are deliberately excluded.

**Grounding:** built from a frequency scan of `docs/**/*.md`, `app/`, `modules/`,
and `config/*.yaml`, cross-referenced against `modules/frameworks/engines/framework_catalog.py`
(`FRAMEWORK_CATALOG`, `FRAMEWORK_CODE_MAP`), `modules/operations/engines/supplementary_query_catalog.py`,
`config/common_control_rules.yaml`, and the framework reference docs under
`docs/01-product/product/`.

Last generated: 2026-09-01.

---

## Glossary

| Abbreviation | Full Form | Definition (ECS context) | Context (module / page) |
|---|---|---|---|
| AI‑SDLC / AISDLC | AI Software Development Life Cycle | ECS's governance model and documentation set for how AI/LLM features are specified, built, reviewed and operated. | `modules/ai_sdlc/`, `docs/03-development/ai-sdlc/` |
| AML | Anti‑Money Laundering | Transaction-screening / financial-crime control area referenced in DPSC and RBI payment-channel controls. | `framework_catalog._dpsc_catalog`, `_rbi_cyber_catalog` |
| AppSec / APS | Application Security | Framework covering SAST/DAST/SCA/secure-code-review controls; catalog key `AppSec`, code prefix `APS`. | `framework_catalog._appsec_catalog`, `/framework/AppSec` |
| ASST / ASS | Application Security Self‑Assessment | Internal pre-assessment framework (ASST‑01…ASST‑17) an app owner completes before formal review; catalog key `ASST`, code prefix `ASS`. | `framework_catalog._asst_catalog`, `/framework/ASST`, `docs/01-product/product/ISG_ASSESSMENT.md` |
| ASV | Approved Scanning Vendor | PCI DSS Req 11 external vulnerability-scan evidence type. | `framework_catalog._pci_catalog`, `ECS_FRAMEWORK_REFERENCE.md` |
| BCM | Business Continuity Management | Continuity policy/programme controls under ITDRM. | `framework_catalog._itdrm_catalog` |
| BCP | Business Continuity Plan | Continuity plan artifact evidenced under ITDRM / ITPP. | `framework_catalog._itdrm_catalog`, `_itpp_catalog` |
| CAB | Change Advisory Board | Change-approval body; CAB minutes are a required evidence artifact for PCI/ITPP change control; exception governance uses a "CAB‑style" approval. | `ECS_CONTROL_REFERENCE_GUIDE.md`, exception-governance flow |
| CBS | Core Banking System | The bank's core ledger application; one of the demo applications and a PCI CDE component. | `framework_catalog.APPLICATIONS`/`SERVERS` (`CBS_ORACLE_CLUSTER`), `config` app inventory |
| CCMP | Cyber Crisis Management Plan | RBI Cyber Security Framework Annex 1.2 evidence artifact. | `framework_catalog._rbi_cyber_catalog` |
| CDE | Cardholder Data Environment | PCI DSS scope boundary; controls target CDE access, segmentation, MFA and encryption. | `framework_catalog._pci_catalog` |
| CIS | Center for Internet Security | Source of the benchmark scans used as OS / container / DB hardening evidence. | `framework_catalog._os_catalog`, `_db_catalog` |
| CISO | Chief Information Security Officer | Persona / reviewer role in enterprise architecture and governance docs. | `docs/02-architecture/architecture/`, persona guides |
| CLE‑* | Cloud Encryption (CloudKMS) | Predefined-query ID prefix for permanently-mock cloud control-plane encryption-at-rest checks (e.g. `CLE-AWS-AURORA-EAR`), one per (provider, technology). | `supplementary_query_catalog.CLOUD_KMS_QUERIES`, `config/mock_cloud_encryption_evidence.yaml` |
| CMDB | Configuration Management Database | Asset-inventory source of truth; reconciliation reports are evidence for OS/RBI/ASST asset-coverage controls; also an evidence collection `source`. | `framework_catalog._os_catalog`, `_rbi_cyber_catalog`, connector sources |
| CMEK | Customer‑Managed Encryption Keys | GCP encryption-at-rest key model checked by the `CLE-GCP-*` cloud-encryption queries. | `supplementary_query_catalog`, `common_control_demo_fixtures` |
| CSITE / C‑SITE / CSI | Cyber Security & IT Examination `†` | RBI-aligned continuous security-operations framework (SOC monitoring, SIEM alert review, escalation TAT, log retention); catalog key `CSITE`, code prefix `CSI`. **Expansion unresolved — four conflicting forms in the repo; see [Uncertain](#uncertain--needs-review).** | `framework_catalog._csite_catalog`, `/framework/CSITE`, `config/framework_control_master/catalog.yaml`, `docs/01-product/product/C-SITE.md` |
| CVE | Common Vulnerabilities and Exposures | Vulnerability identifier used in VAPT / AppSec / SCA remediation evidence. | `framework_catalog._appsec_catalog`, `_vapt_catalog` |
| CWPP | Cloud Workload Protection Platform | Cloud workload / container runtime protection control under C‑SITE. | `framework_catalog._csite_catalog` |
| DAST | Dynamic Application Security Testing | Runtime app-scanning control and evidence type under AppSec. | `framework_catalog._appsec_catalog` |
| DLP | Data Leak / Loss Prevention | Data-exfiltration control under C‑SITE and RBI (Annex 1.13). | `framework_catalog._csite_catalog`, `_rbi_cyber_catalog` |
| DMZ | Demilitarized Zone | Network security zone (e.g. `NGINX_EDGE_DMZ_01`) in the bank-deployment architecture. | `ENTERPRISE_ARCHITECTURE.md`, `framework_catalog.SERVERS` |
| DPSC | Digital Payment Security Controls | RBI framework for net-banking / mobile / UPI / card payment channel security; catalog key and code `DPSC`. | `framework_catalog._dpsc_catalog`, `/framework/DPSC`, `docs/01-product/product/DPSC.md` |
| DR | Disaster Recovery | Recovery-site controls and evidence (drills, switchover attestations); a distinct environment value alongside Production/UAT. | `framework_catalog._itdrm_catalog`, `ENVIRONMENTS` |
| DBB | DB Baselining | Database-hardening framework (SSL, password encryption, replication, audit); catalog key `DB Baselining`, code prefix `DBB`. | `framework_catalog._db_catalog` |
| EAR | Encryption At Rest | Automated common-control encryption-at-rest verdict (IMPLEMENTED / PARTIAL / NOT_IMPLEMENTED) at onboarding — checks storage/disk KMS/CMEK encryption and Oracle TDE wallet/tablespace status. Confirmed: `EAR-*` rules carry `control: encryption-at-rest` (common control `CC-ENCRYPTION_AT_REST`). | `config/common_control_rules.yaml` (`EAR-*` rules), `common_control_demo_fixtures.py`, `tests/test_ear_eit_onboarding_demo.py` |
| EIT | Encryption In Transit | The TLS/SSL companion verdict to EAR — checks DB SSL (`SHOW ssl` / `require_secure_transport`) and NGINX TLS protocol/cipher posture, aggregated per technology. Confirmed: `EIT-*` rules carry `control: encryption-in-transit` under the YAML "Encryption in Transit" section (`CC-ENCRYPTION_IN_TRANSIT`). | `config/common_control_rules.yaml` (`EIT-*` rules), `common_control_rule_engine.aggregate_verdicts`, `tests/test_ear_eit_onboarding_demo.py` |
| EVR | Evidence Requirement | Leaf node of the Framework Control Master hierarchy (policy → control → procedure → evidence requirement), e.g. `PCI-EVR-011`. | `framework_control_master`, `fcm_evidence_demo_seed.py` |
| FCM | Framework Control Master | ECS's canonical catalogue of frameworks → policies → controls → procedures → evidence requirements, wired into the Evidence Dashboard framework-progress computation. | `/mvp/framework-control-master`, `modules/frameworks/`, `config/framework_control_master/` |
| FIM | File Integrity Monitoring | OS-hardening control (critical-file change detection) with alert-summary evidence. | `framework_catalog._os_catalog` |
| FIPS | Federal Information Processing Standards | Cryptographic-module compliance reference in security architecture docs. | `docs/03-development/ai-sdlc/ECS_AI_SECURITY_ARCHITECTURE.md` |
| FTE | Full‑Time Equivalent | Staffing unit in ROI / capacity models. | `strategy/`, `reports/capacity_benchmarks/` |
| GRC | Governance, Risk & Compliance | The overall domain ECS serves; also names external tools (e.g. "ServiceNow GRC") used as evidence sources. | project-wide; `framework_catalog.SOURCES` |
| HSM | Hardware Security Module | Key-custody device; key-management sign-off / HSM inventory are PCI and payments-crypto evidence. | `framework_catalog._pci_catalog`, `_dpsc_catalog` |
| HSTS | HTTP Strict Transport Security | Web-hardening header checked in Nginx/edge TLS posture. | `framework_catalog._nginx_catalog`, hardening guides |
| IAM | Identity and Access Management | Access-control platform; MFA enforcement / access recert evidence originates here. | `framework_catalog._pci_catalog`, `_rbi_cyber_catalog` |
| IOC | Indicator of Compromise | Threat-intel match/closure evidence under C‑SITE and ISO A.5.7. | `framework_catalog._csite_catalog`, `_iso27001_catalog` |
| ISG | Information Security Governance | Internal enterprise governance framework (ISG‑01…ISG‑18: charter, RACI, risk framework, exceptions, KRI dashboard); catalog key and code `ISG`. Owns RAF approval routing for security-impacting risk acceptances. | `framework_catalog._isg_catalog`, `/framework/ISG` |
| ISMS | Information Security Management System | The management-system concept ISO 27001 certifies. | `framework_catalog._iso27001_catalog` |
| ISO 27001 / ISO27001 | ISO/IEC 27001:2022 | Information-security management standard; Annex A controls form the catalog; key `ISO27001`, code prefix `ISO`. | `framework_catalog._iso27001_catalog` |
| ITDRM / DRM | IT Disaster Recovery Management | Resilience, recovery and continuity framework (BCM policy, DR drills, RPO/RTO); catalog key `ITDRM`, code prefix `DRM`. | `framework_catalog._itdrm_catalog`, `/framework/ITDRM` |
| ITPP | Information Technology Policies & Procedures | Operational-governance framework (DR, backup, change, incident/problem, RCA); catalog key and code `ITPP`. Surfaces as the "ITPP command center". Expansion confirmed by three independent code sources (`framework_catalog._itpp_catalog` docstring, `workflow_module.py` description, `generate_framework_control_master_catalog.py` `display_name`); `ECS_FRAMEWORK_REFERENCE.md`'s "IT process & production controls" is a lone paraphrase. | `framework_catalog._itpp_catalog`, `modules/governance/engines/workflow_module.py`, `config/framework_control_master/catalog.yaml`, `/framework/ITPP` |
| JWKS | JSON Web Key Set | Key-set endpoint used by ECS SSO/OIDC token validation. | `app/auth/`, `docs/03-development/production/ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md` |
| JWT | JSON Web Token | Session/auth token format when ECS auth is enabled. | `app/auth/` |
| KPI | Key Performance Indicator | Compliance/operational metrics surfaced on dashboards; ECS ships a KPI dictionary. | `docs/01-product/product/ECS_MASTER_KPI_DICTIONARY.md`, executive dashboards |
| KRI | Key Risk Indicator | Risk-trend metrics on the ISG dashboard. | `framework_catalog._isg_catalog` |
| LLM | Large Language Model | Optional AI backend (Ollama local or Gemini) for grounded/cited answers, summaries and RCA drafts. | `rag.py`, `modules/audit_intelligence/`, `docs/03-development/ai-sdlc/` |
| MFA | Multi‑Factor Authentication | Authentication-strength control; enforcement screenshots/matrices are PCI Req 8, RBI Annex 1.9, ASST‑05 evidence. | `framework_catalog._pci_catalog`, `_rbi_cyber_catalog`, `_asst_catalog` |
| MBSS | Minimum Baseline Security Standard | Enterprise minimum security baseline for production banking systems (privileged-access review, segmentation, centralized logging, patch compliance, secure config, admin MFA). Expansion confirmed by code (`generate_framework_control_master_catalog.py` `display_name`). **It IS a catalog framework — in the FCM catalog** (`config/framework_control_master/frameworks/mbss.yaml`, code `MBSS`), but **not** in the legacy static `framework_catalog.FRAMEWORK_CATALOG`; older docs that say "not a catalog key" predate the FCM catalog. | `config/framework_control_master/`, `scripts/generate_framework_control_master_catalog.py`, `modules/governance/engines/fcm_evidence_progress_engine.py` |
| MTTR | Mean Time To Repair/Resolve | Incident-response SLA metric under C‑SITE. | `framework_catalog._csite_catalog` |
| MVP | Minimum Viable Product | Prefix for the primary server-rendered route group (`/mvp/...`) that hosts most ECS screens. | `modules/shared/routes/routes_mvp.py` |
| NPCI | National Payments Corporation of India | UPI scheme operator; NPCI encryption-compliance letter is DPSC evidence. | `framework_catalog._dpsc_catalog` |
| OBS | Observations | Post-validation finding entities (raise → track → close) that feed the audit lifecycle. | `ECS_BUSINESS_PROCESS_MODEL.md`, `modules/governance/` |
| OIDC | OpenID Connect | SSO protocol for optional ECS enterprise authentication. | `app/auth/`, `ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md` |
| OSB | OS Baselining | Operating-system hardening framework (CIS scans, patch posture, extended-support risk); catalog key `OS Baselining`, code prefix `OSB`. | `framework_catalog._os_catalog` |
| OWASP | Open Worldwide Application Security Project | Reference for AppSec testing controls (Top 10, ASVS). | `framework_catalog._appsec_catalog` |
| PAM | Privileged Access Management | Privileged-session recording/monitoring; sample PAM session logs are PCI Req 8 and C‑SITE evidence. | `framework_catalog._pci_catalog`, `_csite_catalog` |
| PII | Personally Identifiable Information | Sensitive-data category governing classification, DLP and inventory controls. | `framework_catalog._isg_catalog`, security architecture docs |
| PIR | Post‑Incident Review | Emergency-release / major-incident review artifact under AppSec and C‑SITE. | `framework_catalog._appsec_catalog`, `_csite_catalog` |
| PQ | Predefined Query | A registered, deterministic read-only check against a target technology (e.g. `PGX-001`); the unit of automated evidence collection. | `modules/operations/engines/predefined_queries_engine.py`, `config/predefined_query_phase1_registry.yaml` |
| PSP | Payment Service Provider | Third-party payment integration assessed under DPSC (security assessment, key rotation). | `framework_catalog._dpsc_catalog` |
| QSA | Qualified Security Assessor | PCI DSS assessor role; "QSA readiness" is a PCI dashboard tile. | `ECS_FEATURE_REFERENCE.md`, PCI framework tiles |
| RAF | Risk Acceptance Form | First-class, durable exception/risk-acceptance artifact (owner sign-off, risk rating, expiry, compensating control, ISG approval routing). | `docs/01-product/use-cases/phase2/ECS_RAF_IMPLEMENTATION_PLAN.md`, exception governance |
| RAG | Retrieval‑Augmented Generation | The grounded-answer pattern: retrieve evidence chunks, then have the LLM answer with citations. | `rag.py`, prompt/audit workbenches |
| RBAC | Role‑Based Access Control | ECS's authorization model (personas → allowed actions/routes). | `app/auth/`, `ECS_ROLE_ACTION_MATRIX.md`, `ECS_RBAC_LEGACY_FLAWS.md` |
| RBI | Reserve Bank of India | Indian banking regulator; "RBI Cyber Security" framework (Annex 1.1–1.24) has catalog key `RBI Cyber Security`, code prefix `RBI`. | `framework_catalog._rbi_cyber_catalog`, `/framework/RBI` |
| RCA | Root Cause Analysis | Problem-management narrative drafted (optionally LLM-assisted) from ITPP problem data. | `modules/operations/` ITPP command center |
| RPO | Recovery Point Objective | Data-loss tolerance declared in DR / ASST‑10 evidence. | `framework_catalog._itdrm_catalog`, `_asst_catalog` |
| RTO | Recovery Time Objective | Recovery-time target declared in DR / ASST‑10 evidence. | `framework_catalog._itdrm_catalog`, `_asst_catalog` |
| SAST | Static Application Security Testing | Source-code scanning control and evidence type under AppSec (SonarQube in the demo stack). | `framework_catalog._appsec_catalog` |
| SBOM | Software Bill of Materials | CI-generated dependency inventory; generation + drift detection is an AppSec control. | `framework_catalog._appsec_catalog` |
| SCA | Software Composition Analysis | Third-party dependency vulnerability scanning under AppSec. | `framework_catalog._appsec_catalog` |
| SDLC | Software Development Life Cycle | Secure-SDLC controls (RBI Annex 1.6); see also AI‑SDLC. | `framework_catalog._rbi_cyber_catalog` |
| SIEM | Security Information and Event Management | Log-aggregation/alerting platform; SIEM exports are an evidence `source` and the basis of C‑SITE monitoring controls (`SIEM_COLLECTOR_HQ`). | `framework_catalog._csite_catalog`, `SOURCES` |
| SLA | Service Level Agreement | Time-bound commitment (e.g. remediation within SLA); ECS tracks SLA aging and escalation. | `ECS_SLA_ESCALATION_MATRIX.md`, workflow engine |
| SoA | Statement of Applicability | ISO 27001 control-applicability document; "SoA coverage" is an ISO dashboard tile. | `framework_catalog._iso27001_catalog`, ISO tiles |
| SOAR | Security Orchestration, Automation and Response | Playbook-automation control under C‑SITE (run summaries, failure remediation). | `framework_catalog._csite_catalog` |
| SOC | Security Operations Centre | 24×7 monitoring function; "SOC Production" is an environment value; distinct from SOC2. | `framework_catalog.ENVIRONMENTS`, `_csite_catalog` |
| SOC 2 / SOC2 | System and Organization Controls 2 | Trust Services Criteria framework (Security, Availability, Confidentiality, Processing Integrity); catalog key `SOC2`, code prefix `SOC`. | `framework_catalog._soc2_catalog` |
| SoD | Segregation of Duties | Access-conflict control; SoD conflict remediation is PCI Req 7 and RBI Annex 1.8 evidence. | `framework_catalog._pci_catalog`, `_rbi_cyber_catalog` |
| SSO | Single Sign‑On | Optional enterprise authentication mode for ECS (via OIDC). | `app/auth/`, `ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md` |
| SSRF | Server‑Side Request Forgery | Web vulnerability class in AppSec / hardening guidance. | `docs/03-development/production/PRODUCTION_HARDENING_GUIDE.md` |
| TAT | Turnaround Time | Alert/incident escalation-and-closure window tracked under C‑SITE (P1/P2 TAT). | `framework_catalog._csite_catalog`, `docs/01-product/product/C-SITE.md` |
| TD | Technical Debt | Exception category raised at `/mvp/exceptions`; TD exceptions carry risk exposure and reduce dynamic completeness via a penalty. | `modules/governance/engines/missing_evidence_engine.py`, `/mvp/exception-governance` |
| TDE | Transparent Data Encryption | Database encryption-at-rest mechanism; TDE attestation is PCI Req 3 and SQL Server (`MSX-007`) evidence. | `framework_catalog._pci_catalog`, `supplementary_query_catalog` |
| TLS | Transport Layer Security | Encryption-in-transit protocol; cipher/cert evidence underpins PCI Req 4, Nginx Baselining and the EIT common-control check. | `framework_catalog._nginx_catalog`, `_pci_catalog`, `common_control_rules.yaml` |
| TPSP | Third‑Party Service Provider | Vendor/outsourcing party assessed under PCI, RBI Annex 1.22 and VAPT third-party evidence. | `framework_catalog._pci_catalog`, `_rbi_cyber_catalog`, `_vapt_catalog` |
| UAT | User Acceptance Testing | A deployment environment/target set and the asset-driven scheduler's primary context. | `framework_catalog.ENVIRONMENTS`, `docs/02-architecture/design/UAT_ASSET_DRIVEN_SCHEDULER_DESIGN.md` |
| UPI | Unified Payments Interface | Indian real-time payment rail; a demo application and DPSC channel (`UPI_SWITCH_CLUSTER`). | `framework_catalog.APPLICATIONS`, `_dpsc_catalog` |
| VA | Vulnerability Assessment | Scan-based vulnerability identification (internal/external/DB/cloud/wireless); paired with pen-testing as VAPT. | `framework_catalog._vapt_catalog` |
| VAPT | Vulnerability Assessment and Penetration Testing | Framework and evidence set for scanning + pen-testing banking apps; catalog key `VAPT`, code prefix `VAP`. | `framework_catalog._vapt_catalog`, `/framework/VAPT`, `docs/01-product/product/VAPT.md` |
| WAF | Web Application Firewall | Edge-filtering control; WAF rule exports/effectiveness are AppSec, DPSC and Nginx evidence. | `framework_catalog._appsec_catalog`, `_dpsc_catalog` |
| WCAG | Web Content Accessibility Guidelines | Accessibility standard applied to ECS UI (chart/contrast remediation). | `nav_audit/chart_accessibility_remediation_v1.md` |

### Predefined-query technology ID prefixes

Predefined queries are identified as `<PREFIX>-NNN`. Each prefix denotes the
target technology (`supplementary_query_catalog.py`,
`config/predefined_query_phase1_registry.yaml`):

| Prefix | Technology |
|---|---|
| `PGX-` | PostgreSQL |
| `YBX-` | YugabyteDB (YSQL) |
| `MYX-` | Aurora MySQL / MySQL |
| `ORX-` | Oracle Database |
| `MSX-` | Microsoft SQL Server |
| `MGX-` | MongoDB |
| `RDX-` | Redis |
| `ASX-` | Aerospike |
| `NGX-` | NGINX (also the Nginx Baselining framework code) |
| `APX-` | Apache HTTP Server |
| `TCX-` | Apache Tomcat |
| `LNX-` | Linux OS |
| `K8X-` | Kubernetes |
| `OCX-` | OpenShift |
| `MW-` | Middleware (TLS/config baseline) |
| `CLE-` | Cloud KMS encryption-at-rest (mock) |
| `DB-`, `OS-`, `APP-`, `PCI-` | Generic DB / OS / application / PCI checks |

### Framework catalog codes

From `framework_catalog.FRAMEWORK_CODE_MAP` (the legacy static catalog) — display
name → `framework_code` stored in the repository:

| Code | Framework | Code | Framework |
|---|---|---|---|
| `PCI` | PCI DSS | `SOC2` | SOC 2 |
| `DPSC` | DPSC | `ISO27001` | ISO 27001 |
| `OSB` | OS Baselining | `RBI` | RBI Cyber Security |
| `DBB` | DB Baselining | `ISG` | ISG |
| `NGX` | Nginx Baselining | `ASST` | ASST |
| `APPSEC` | AppSec | `ITPP` | ITPP |
| `VAPT` | VAPT | `ITDRM` | ITDRM |
| `CSITE` | C‑SITE | | |

The **Framework Control Master** catalog (`config/framework_control_master/catalog.yaml`,
generated by `scripts/generate_framework_control_master_catalog.py`) is a separate,
partly-overlapping set with its own codes and `display_name` expansions —
including some not in the legacy map:

| Code | `name` | `display_name` |
|---|---|---|
| `MBSS` | MBSS | Minimum Baseline Security Standard |
| `MWB` | Middleware Baseline | Middleware Baseline |
| `CSI` | C‑SITE | Cyber Security Incident Tracking & Evaluation |
| `OSB` | OS Baseline | Operating System Baseline |
| `DBB` | Database Baseline | Database Baseline |
| `ITPP` | ITPP | Information Technology Policies & Procedures |
| `ASST` | ASST | Application Security Self-Assessment |
| `PCI` | PCI DSS | Payment Card Industry Data Security Standard |
| `DPSC` | DPSC | Digital Payment Security Controls |
| `VAP` | VAPT | Vulnerability Assessment & Penetration Testing |

---

## Uncertain — needs review

These appeared with meaningful frequency but their ECS-specific meaning is
ambiguous, inconsistent across sources, or possibly noise. Confirm before
relying on them.

> **Resolved in the 2026-09-01 review pass** (moved to the main table): **ITPP**
> ("Information Technology Policies & Procedures" — 3 code sources agree),
> **EAR** ("Encryption At Rest") and **EIT** ("Encryption In Transit") — both
> confirmed against `config/common_control_rules.yaml` rule `control:` values and
> the `test_ear_eit_onboarding_demo.py` assertions, and **MBSS** ("Minimum
> Baseline Security Standard" — confirmed by `generate_framework_control_master_catalog.py`;
> it is a real FCM-catalog framework).

| Abbreviation | Observed as | Why still uncertain |
|---|---|---|
| C‑SITE `†` | **Four** distinct expansions in the repo — two of them in code and mutually inconsistent: (1) "Cyber Security & IT Examination" (`docs/01-product/product/C-SITE.md`); (2) "Cyber security incident & threat" (`ECS_FRAMEWORK_REFERENCE.md`, ×2); (3) "Cyber Security Incident Tracking & Evaluation" (`config/framework_control_master/catalog.yaml` + `generate_framework_control_master_catalog.py`, matching code prefix `CSI`); (4) "Cyber Security IT Evaluation" (`modules/governance/engines/workflow_module.py`). `framework_catalog._csite_catalog()` has **no docstring**. | No single authority. The framework *key* `CSITE` is letter-accurate only for reading #1 (C‑S‑IT‑E), which also matches RBI's real "Cyber Security and IT Examination (CSITE) Cell"; the *code* `CSI` and the FCM `display_name` point to reading #3. **Recommended canonical: "Cyber Security & IT Examination"** — but this needs a framework owner's decision, and ideally one code source should be corrected to match. |
| CLE‑ (query-ID prefix) | Prefix of the mock cloud-encryption predefined queries (`CLE-AWS-AURORA-EAR`, `CLE-GCP-*-EAR`). Confirmed: the queries belong to the `_CLOUDKMS` / `"CloudKMS"` technology group and the `-EAR` suffix is Encryption At Rest. The **`CLE` prefix itself is never expanded** in any comment, docstring, config note, or commit message. | "Cloud Encryption" is the obvious reading of `CLE` given the full ID shape `CLE-<provider>-<tech>-EAR`, but it is **inferred, unconfirmed** — no source states it. |
| ASST vs ASX | `ASST` = Application Security Self-Assessment (framework, code `ASS`); `ASX` = Aerospike predefined-query prefix | Not a meaning gap — a collision hazard. Similar tokens, unrelated referents; ensure tooling / search does not conflate them. |
| EVR / POL / PROC | FCM hierarchy node types (evidence requirement / policy / procedure) | Used only as ID fragments (`PCI-EVR-011`, `PCI-POL-NETWORK-01`, `PCI-PROC-01`); real terms, but never formally listed as abbreviations. Documented under [FCM](#glossary) / EVR row. |
| SOURCE, ANCHOR, OWNERS | High raw frequency in the caps scan | Python/SQL identifiers, dict keys and Mermaid node labels — not domain acronyms. Excluded from the main table; listed here only to record that they were reviewed and dismissed. |
| CS / CSI / VP / DP / TD (2-letter control-domain codes) | Appear inside `governance_data_enrichment.py` control IDs like `NGX-C-01`, `VP-C-02`, `DP-C-04` | Positional per-domain control-ID letters, not standalone abbreviations. (Note: `CSI` here is unrelated to the C‑SITE framework code `CSI`.) |

---

`†` Expansion is not settled by the codebase — the glossary lists the
best-supported form but a framework owner should confirm it. See the row in
[Uncertain — needs review](#uncertain--needs-review).
