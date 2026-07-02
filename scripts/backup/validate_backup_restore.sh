#!/usr/bin/env bash
# ECS backup/restore validation drill (Phase 5 Step 1).
#
# Proves a backup is restorable WITHOUT touching production data:
#   1. Take a fresh backup of the live repository DB.
#   2. Create a disposable temp DB.
#   3. Restore the backup into the temp DB.
#   4. Compare row counts of key tables (source vs restored).
#   5. Drop the temp DB.
#
# Usage:
#   scripts/backup/validate_backup_restore.sh [--keep] [--temp-db NAME]
#
# Options:
#   --temp-db NAME   Name of disposable DB (default: ecs_restore_test_<ts>).
#   --keep           Do not drop the temp DB at the end (for inspection).
#   -h, --help       Show this help.
#
# Read-only against the source DB; the temp DB is created and dropped here.

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_env.sh"

KEEP=0
TEMP_DB=""

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --temp-db) TEMP_DB="${2:?--temp-db requires a name}"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (use --help)" ;;
  esac
done

require_tool pg_dump
require_tool pg_restore
require_tool psql

TEMP_DB="${TEMP_DB:-ecs_restore_test_$(date -u +%Y%m%d%H%M%S)}"
HOST="${ECS_REPO_PG_HOST}"; PORT="${ECS_REPO_PG_PORT}"
USER="${ECS_REPO_PG_USER}"; SRC_DB="${ECS_REPO_PG_DATABASE}"
export PGPASSWORD="${ECS_REPO_PG_PASSWORD}"

# Tables whose row counts must match after restore. Missing tables count as 0 on
# both sides, so the drill stays valid across schema evolution.
CHECK_TABLES=(evidence audit_log observations frameworks controls)

count_rows() {
  local db="$1" tbl="$2"
  psql --host="${HOST}" --port="${PORT}" --username="${USER}" --dbname="${db}" -tAc \
    "SELECT count(*) FROM to_regclass('public.${tbl}') IS NOT NULL
       AND EXISTS (SELECT 1) ;" >/dev/null 2>&1 || true
  # Reliable count: returns 0 when table is absent.
  psql --host="${HOST}" --port="${PORT}" --username="${USER}" --dbname="${db}" -tAc \
    "SELECT CASE WHEN to_regclass('public.${tbl}') IS NULL THEN 0
                 ELSE (SELECT count(*) FROM public.${tbl}) END;" 2>/dev/null | tr -d '[:space:]'
}

cleanup() {
  if [[ "${KEEP}" -eq 1 ]]; then
    log "Keeping temp DB ${TEMP_DB} (--keep)."
    return
  fi
  log "Dropping temp DB ${TEMP_DB}"
  psql --host="${HOST}" --port="${PORT}" --username="${USER}" --dbname=postgres \
    -c "DROP DATABASE IF EXISTS \"${TEMP_DB}\"" >/dev/null 2>&1 || true
}
trap cleanup EXIT

log "=== ECS backup/restore validation drill ==="
log "Source: $(describe_target "${HOST}" "${PORT}" "${SRC_DB}" "${USER}")"

# 1) Backup
log "[1/4] Taking backup of ${SRC_DB}"
"$(dirname "${BASH_SOURCE[0]}")/backup.sh" --retention 0 >/dev/null
LATEST="$(ls -1t "${BACKUP_DIR}"/ecs_repository_*.dump 2>/dev/null | head -n1 || true)"
[[ -n "${LATEST}" ]] || die "no backup produced"
log "      backup: ${LATEST}"

# 2) Temp DB
log "[2/4] Creating temp DB ${TEMP_DB}"
psql --host="${HOST}" --port="${PORT}" --username="${USER}" --dbname=postgres \
  -c "DROP DATABASE IF EXISTS \"${TEMP_DB}\"" >/dev/null
psql --host="${HOST}" --port="${PORT}" --username="${USER}" --dbname=postgres \
  -c "CREATE DATABASE \"${TEMP_DB}\"" >/dev/null

# 3) Restore
log "[3/4] Restoring into ${TEMP_DB}"
pg_restore --host="${HOST}" --port="${PORT}" --username="${USER}" --dbname="${TEMP_DB}" \
  --no-owner --no-privileges "${LATEST}" >/dev/null 2>&1 \
  || log "      pg_restore finished with warnings"

# 4) Verify counts
log "[4/4] Verifying row counts (source vs restored)"
FAIL=0
printf '%-16s %12s %12s %8s\n' "TABLE" "SOURCE" "RESTORED" "STATUS" >&2
for tbl in "${CHECK_TABLES[@]}"; do
  src="$(count_rows "${SRC_DB}" "${tbl}")"
  dst="$(count_rows "${TEMP_DB}" "${tbl}")"
  src="${src:-0}"; dst="${dst:-0}"
  if [[ "${src}" == "${dst}" ]]; then
    status="OK"
  else
    status="MISMATCH"; FAIL=1
  fi
  printf '%-16s %12s %12s %8s\n' "${tbl}" "${src}" "${dst}" "${status}" >&2
done

if [[ "${FAIL}" -ne 0 ]]; then
  die "validation FAILED: row counts differ between source and restored DB"
fi

log "=== VALIDATION PASSED: backup is restorable and row counts match ==="
