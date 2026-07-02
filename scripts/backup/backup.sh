#!/usr/bin/env bash
# ECS database backup (Phase 5 Step 1).
#
# Creates a timestamped, compressed pg_dump of the ECS evidence repository (the
# durable system of record: evidence, audit_log, observations, frameworks, ...).
# Optionally also backs up the vector store.
#
# Usage:
#   scripts/backup/backup.sh [--vector] [--out DIR] [--retention DAYS] [--plain]
#
# Options:
#   --vector            Also back up the vector store DB (ECS_VECTOR_PG_*).
#   --out DIR           Output directory (default: $BACKUP_DIR or <repo>/backups).
#   --retention DAYS    Prune backups older than DAYS (default: $BACKUP_RETENTION_DAYS).
#   --plain             Also emit a plain-SQL .sql alongside the custom .dump.
#   -h, --help          Show this help.
#
# Connection comes from ECS_REPO_PG_* (see config/repository.yaml). No secrets are
# printed. Exit non-zero on any failure.

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_env.sh"

WITH_VECTOR=0
ALSO_PLAIN=0

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vector) WITH_VECTOR=1; shift ;;
    --out) BACKUP_DIR="${2:?--out requires a directory}"; shift 2 ;;
    --retention) BACKUP_RETENTION_DAYS="${2:?--retention requires days}"; shift 2 ;;
    --plain) ALSO_PLAIN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (use --help)" ;;
  esac
done

require_tool pg_dump

mkdir -p "${BACKUP_DIR}"
TS="$(timestamp)"

# Back up one database to a custom-format dump (and optionally plain SQL).
backup_one() {
  local host="$1" port="$2" db="$3" user="$4" pass="$5" label="$6"
  local base="ecs_${label}_${TS}"
  local dump_path="${BACKUP_DIR}/${base}.dump"

  log "Backing up ${label} ($(describe_target "${host}" "${port}" "${db}" "${user}")) -> ${dump_path}"
  PGPASSWORD="${pass}" pg_dump \
    --host="${host}" --port="${port}" --username="${user}" --dbname="${db}" \
    --format=custom --no-owner --no-privileges --verbose \
    --file="${dump_path}" 2> "${BACKUP_DIR}/${base}.log" \
    || die "pg_dump failed for ${label}; see ${BACKUP_DIR}/${base}.log"

  # Integrity check: pg_restore --list must parse the archive.
  pg_restore --list "${dump_path}" >/dev/null 2>&1 \
    || die "backup integrity check failed (pg_restore --list) for ${dump_path}"

  if command -v sha256sum >/dev/null 2>&1; then
    ( cd "${BACKUP_DIR}" && sha256sum "${base}.dump" > "${base}.dump.sha256" )
  elif command -v shasum >/dev/null 2>&1; then
    ( cd "${BACKUP_DIR}" && shasum -a 256 "${base}.dump" > "${base}.dump.sha256" )
  fi

  if [[ "${ALSO_PLAIN}" -eq 1 ]]; then
    PGPASSWORD="${pass}" pg_dump \
      --host="${host}" --port="${port}" --username="${user}" --dbname="${db}" \
      --format=plain --no-owner --no-privileges \
      --file="${BACKUP_DIR}/${base}.sql" \
      || die "plain pg_dump failed for ${label}"
  fi

  local size
  size="$(du -h "${dump_path}" | cut -f1)"
  log "OK  ${label}: ${dump_path} (${size})"
}

backup_one "${ECS_REPO_PG_HOST}" "${ECS_REPO_PG_PORT}" "${ECS_REPO_PG_DATABASE}" \
           "${ECS_REPO_PG_USER}" "${ECS_REPO_PG_PASSWORD}" "repository"

if [[ "${WITH_VECTOR}" -eq 1 ]]; then
  backup_one "${ECS_VECTOR_PG_HOST}" "${ECS_VECTOR_PG_PORT}" "${ECS_VECTOR_PG_DATABASE}" \
             "${ECS_VECTOR_PG_USER}" "${ECS_VECTOR_PG_PASSWORD}" "vectors"
fi

# --- Retention: prune dumps/logs/checksums older than BACKUP_RETENTION_DAYS --------
if [[ "${BACKUP_RETENTION_DAYS}" -gt 0 ]]; then
  log "Pruning backups older than ${BACKUP_RETENTION_DAYS} day(s) in ${BACKUP_DIR}"
  find "${BACKUP_DIR}" -maxdepth 1 -type f \
    \( -name 'ecs_*.dump' -o -name 'ecs_*.sql' -o -name 'ecs_*.log' -o -name 'ecs_*.sha256' \) \
    -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete 2>/dev/null || true
fi

log "Backup complete. Latest artifacts in ${BACKUP_DIR}"
