# ECS Framework Reference Library

**Type:** Framework reference index. **No code/UI/DB changes.** **Grounding:** `modules/frameworks/engines/framework_catalog.py` (`FRAMEWORK_CATALOG`, 15 frameworks / 305 controls), framework routes (`/framework/{name}`), `framework_kpi_drill_engine`.

> ECS ships **15 frameworks** in `FRAMEWORK_CATALOG`: PCI DSS, DPSC, OS Baselining, DB Baselining, Nginx Baselining, AppSec, VAPT, CSITE, ITPP, ITDRM, SOC2, ISO27001, RBI Cyber Security, ISG, ASST.

## Catalog frameworks (in `FRAMEWORK_CATALOG`)

| Framework | Doc | Catalog key |
|---|---|---|
| PCI DSS | [PCI_DSS.md](PCI_DSS.md) | `PCI DSS` |
| DPSC (Digital Payment Security Controls) | [DPSC.md](DPSC.md) | `DPSC` |
| C-SITE | [C-SITE.md](C-SITE.md) | `CSITE` |
| ISG Assessment | [ISG_ASSESSMENT.md](ISG_ASSESSMENT.md) | `ISG` + `ASST` |
| ITPP | [ITPP.md](ITPP.md) | `ITPP` |
| ITDRM | [ITDRM.md](ITDRM.md) | `ITDRM` |
| VAPT | [VAPT.md](VAPT.md) | `VAPT` |
| Application Security | [APPLICATION_SECURITY.md](APPLICATION_SECURITY.md) | `AppSec` |
| OS Baselining | [OS_BASELINING.md](OS_BASELINING.md) | `OS Baselining` |
| Database Baselining | [DATABASE_BASELINING.md](DATABASE_BASELINING.md) | `DB Baselining` |
| Nginx Baselining | [NGINX_BASELINING.md](NGINX_BASELINING.md) | `Nginx Baselining` |

## Requested frameworks not in catalog — **[Inferred/Target]**

| Framework | Doc | Closest catalog coverage |
|---|---|---|
| Middleware Baselining | [MIDDLEWARE_BASELINING.md](MIDDLEWARE_BASELINING.md) | OS/DB Baselining + middleware controls in OS catalog |
| Cloud Security | [CLOUD_SECURITY.md](CLOUD_SECURITY.md) | Prisma Cloud connector + container/baseline controls |
| AI Governance | [AI_GOVERNANCE.md](AI_GOVERNANCE.md) | AI Governance posture + AI-SDLC (`docs/AI/`) |
| Mobile Banking Security | [MOBILE_BANKING_SECURITY.md](MOBILE_BANKING_SECURITY.md) | DPSC mobile/payment controls |

> Also in catalog but outside the requested-15: **SOC2**, **ISO27001**, **RBI Cyber Security** (cross-mapping anchors used heavily by reuse engine).

## Common structure
Each framework doc covers: Purpose · Objectives · Controls · Checklist · Evidence Requirements · Control Mapping · Control Reuse · Evidence Reuse · Executive/Audit/Risk Reporting · Sample Assessment/Findings/Closure.

## Related
- Controls model: [ECS_CONTROL_REFERENCE_GUIDE.md](../product/ECS_CONTROL_REFERENCE_GUIDE.md)
- Query-based testing: [ECS_PREDEFINED_QUERY_ARCHITECTURE.md](../OPERATIONS/ECS_PREDEFINED_QUERY_ARCHITECTURE.md)
- KPIs: [ECS_MASTER_KPI_DICTIONARY.md](../product/ECS_MASTER_KPI_DICTIONARY.md)
