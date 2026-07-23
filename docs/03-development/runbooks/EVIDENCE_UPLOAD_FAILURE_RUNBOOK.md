# Runbook: Evidence Upload Failure

Manual/bulk uploads or connector-collected evidence are not landing in the
repository, or the audit-intelligence mirror is missing.

> Reference: [`../evidence-management/ECS_EVIDENCE_REFERENCE_GUIDE.md`](../evidence-management/ECS_EVIDENCE_REFERENCE_GUIDE.md)
> · evidence bridge: `modules/operations/engines/evidence_repository.py`
> (`register_upload` → `_mirror_to_audit_repository`).

## Symptoms
- Upload returns an error; item missing from `/mvp/evidence-health` or readiness;
  `audit_repository_synced: false` on a record; object-store (GCS/MinIO) errors.

## Diagnose
1. `GET /readyz` — 503 means PostgreSQL repository unreachable (see degraded-readiness runbook).
2. Check object-store connectivity (GCS/MinIO creds + bucket + `secure`).
3. For a specific item: `GET /api/evidence/{id}/integrity` (hash verify).
4. Inspect logs for the `Evidence Uploaded` event and any bridge exception
   (the bridge is best-effort and records `audit_repository_synced`).

## Common causes & remediation
| Cause | Fix |
|-------|-----|
| Repository DB down | Restore PostgreSQL (`ECS_REPO_PG_*`); see recovery runbook. |
| Object store misconfigured | Fix `ECS_OBJECT_STORE_*` / bucket / credentials; `secure: true` in prod. |
| Mirror failed (`synced:false`) | Primary upload still succeeds; re-run once the audit-intelligence repo is reachable. |
| Naming/metadata rejected | Validate via `GET /api/evidence/naming-preview`, `POST /api/evidence/validate-metadata`. |
| Integrity mismatch | Investigate tampering; re-upload the source artifact. |

## Verify
- Item appears in the repository with a SHA-256 and `audit_repository_synced: true`.
- `GET /api/evidence/{id}/integrity` reports valid.

## Escalate
Persisted-data issues → [`../operations/RECOVERY_RUNBOOK.md`](../operations/RECOVERY_RUNBOOK.md).
