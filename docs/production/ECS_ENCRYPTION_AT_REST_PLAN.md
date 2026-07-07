# ECS Encryption-at-Rest Plan

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Grounding:** `config/environments/_base.yaml` (`storage.object_store`, `MINIO_SECURE`), `docker-compose.yml` (postgres, minio), `ecs_platform/repository/*` (Postgres), MinIO object store (`ecs-evidence`), backup scripts (`scripts/backup/*`).

> **Scope note:** encryption-at-rest in ECS is predominantly an **infrastructure/configuration** concern (storage volumes, DB engine, object-store server-side encryption, KMS). ECS code references storage via config; no application crypto rewrite is required. `MINIO_SECURE:-false` today governs **TLS in transit** to MinIO, not at-rest — at-rest must be provided by the storage layer.

---

## 1. Scope of data at rest
| Store | Contents | Sensitivity |
|---|---|---|
| PostgreSQL (`ecs_repository`) | evidence metadata, controls, observations, audit log, RBAC | High |
| pgvector (`ecs_vectors`) | embeddings of indexed content | Medium–High |
| MinIO / object store (`ecs-evidence`) | raw evidence artifacts (docs, screenshots, scan outputs) | High |
| Backups | DB dumps + object-store snapshots | High |
| Redis | cache/queue (transient) | Medium |

## 2. Database (PostgreSQL)
- **At rest:** enable encrypted volumes (LUKS/cloud-disk encryption) or managed-Postgres TDE (RDS/Azure DB encryption with CMK).
- **In transit:** require TLS (`sslmode=require/verify-full`) between app and DB.
- **Compliance:** PCI DSS Req 3 (stored data protection), RBI data-localization for keys.
- **Validate:** confirm volume/instance encryption flag; document key custodian.

## 3. Evidence repository (metadata) & pgvector
- Covered by the same encrypted Postgres instance/volume.
- Ensure evidence integrity hashes (SHA-256) remain verifiable post-encryption (encryption is transparent to app reads).

## 4. Object storage (MinIO / S3)
- **MinIO:** enable **SSE** (server-side encryption) with KMS (SSE-KMS) or SSE-S3; set `MINIO_KMS_*`; enable TLS (`MINIO_SECURE=true`) for in-transit.
- **S3 (if `provider=s3`):** default bucket encryption with KMS CMK; enforce `aws:kms`; bucket policy denies unencrypted PUT.
- **Validate:** object metadata shows encryption header; deny unencrypted writes.

## 5. Backups
- Encrypt backup artifacts at creation (e.g., `pg_dump | gpg`/age, or backup tool with KMS) and at the destination (encrypted bucket/volume).
- Validate restore from encrypted backup (`scripts/backup/validate_backup_restore.sh`).
- Off-site copies retain encryption; access via KMS-gated keys only.

## 6. Key management (KMS)
- Use enterprise **KMS/HSM** (Azure Key Vault / AWS KMS / on-prem HSM). No keys in repo/env files; reference via vault.
- Separate keys per store (DB, object, backup); least-privilege key policies; audit key access.
- Document key custodians, dual-control for high-value keys.

## 7. Rotation
- Define rotation cadence (e.g., annual CMK rotation, or per policy); automatic rotation where supported (KMS-managed).
- Re-encryption strategy for envelope keys (data keys rotate without re-encrypting all objects when using envelope encryption).
- Track rotation events in the audit/ops log; alert on overdue rotation.

## 8. Compliance mapping
| Requirement | Control |
|---|---|
| PCI DSS Req 3 | Encrypt stored cardholder/sensitive data + key management |
| PCI DSS Req 4 | Encrypt in transit (TLS) |
| RBI / DPSC | Data protection, key localization, retention |
| ISG / OS-DB baselines | Storage hardening, encryption enabled |

## 9. Effort & ownership
| Item | Effort | Owner |
|---|---|---|
| Encrypted DB volume / managed TDE | 1–2d | Infra/DBA |
| Object-store SSE-KMS + TLS | 1d | Infra |
| Backup encryption + restore validation | 1d | Infra/DevOps |
| KMS setup + key policies + rotation | 1–2d | Security/Infra |
| Compliance evidence capture (for audit) | 0.5d | Compliance |
| **Total** | **~4–6 eng/infra-days** | — |

**Risk:** Medium — mostly infra; main risk is key-management misconfiguration (loss of keys = loss of data). **Mitigation:** KMS with managed durability, documented custody, tested restore.

## Cross-references
- [Production Master Plan](../production/ECS_PRODUCTION_READINESS_MASTER_PLAN.md) · [SSO/OIDC Plan](../production/ECS_SSO_OIDC_IMPLEMENTATION_PLAN.md) · [Security Reference](../production/ECS_SECURITY_REFERENCE.md) · [Backup & Recovery](../operations/ECS_BACKUP_AND_RECOVERY_GUIDE.md)
