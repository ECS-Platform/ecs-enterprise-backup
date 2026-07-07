# Framework Reference — Cloud Security **[Inferred/Target]**

**Status:** **Not a dedicated key in `FRAMEWORK_CATALOG`.** Documented as a target framework. Closest shipped coverage: **Prisma Cloud connector** (`config/integrations.yaml`, interface-complete, disabled by default) + container/baseline controls in **OS Baselining** and **AppSec (Trivy)**. Part of [Frameworks Library](README.md).

## Purpose
Assure cloud posture (CSPM) for cloud-hosted banking workloads — misconfiguration, IAM, encryption, network exposure, container/image security.

## Objectives
CSPM findings management, cloud IAM least-privilege, encryption (at-rest/in-transit), network exposure control, container image scanning, compliance-pack mapping (CIS/PCI cloud).

## Controls (today via connectors/other frameworks)
Prisma Cloud CSPM findings · Trivy image scanning (AppSec) · Container Host/Runtime Baseline (OS Baselining) · TLS/edge (Nginx). **[Inferred/Target]** dedicated cloud IAM/encryption/exposure controls.

## Checklist (target)
- [ ] Prisma Cloud critical findings = 0
- [ ] Cloud IAM least-privilege reviewed
- [ ] Storage/DB encryption enabled
- [ ] No public exposure of sensitive services
- [ ] Image scan gate (Trivy) passing

## Evidence Requirements
Prisma Cloud finding exports, IAM reviews, encryption configs, image scan reports. See [Prisma Cloud Integration](../connectors/PRISMA_CLOUD.md).

## Control & Evidence Reuse
Encryption/vuln/IAM evidence reuse with **PCI DSS, AppSec, VAPT, OS Baselining**.

## Reporting / Sample
- **Executive/Audit/Risk:** cloud posture via integration health + risk register until dedicated framework added.
- **Sample finding [Inferred]:** public storage bucket → restrict + re-scan → Approved.
