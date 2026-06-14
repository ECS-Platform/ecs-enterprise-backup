#!/usr/bin/env bash
# ECS database restore (Phase 5 Step 1).
#
# Restores an ECS evidence-repository backup created by scripts/backup/backup.sh
# into a target database using pg_restore (custom-format archives).
#
# Usage:
#   scripts/restore/restore.sh [--latest | --file PATH] [--db NAME] [--label LABEL]
#                              [--create] [--clean] [--yes] [--jobs N]
#
# Options:
#   --latest        Restore the most recent backup for the label (default action).
#   --file PATH     Restore a specific .dump file (overrides --latest).
#   --label LABEL   Which backup family for --latest: repository (default) | vectors.
#   --db NAME       Target database (default: ECS_REPO_PG_DATABASE, or the vectors DB
#                   when --label vectors). Use a TEST db for drills.
#   --create        Create the target DB if it does not exist.
#   --clean         Drop existing objects before restore (pg_restore --clean).
#   --jobs N        Parallel restore jobs (pg_restore -j N).
#   --yes           Do not prompt for confirmation (for automation).
#   -h, --help      Show this help.
#
# Connection comes from ECS_REPO_PG_* / ECS_VECTOR_PG_*. No secrets are printed.
# DESTRUCTIVE when restoring over a populated database — confirmation is required
# unless --yes is given.

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../backup/_env.sh"

MODE="latest"
FILE=""
LABEL="repository"
TARGET_DB=""
DO_CREATE=0
DO_CLEAN=0
JOBS=1
ASSUME_YES=0

usage() { sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --latest) MODE="latest"; shift ;;
    --file) MODE="file"; FILE="${2:?--file requires a path}"; shift 2 ;;
    --label) LABEL="${2:?--label requires a value}"; shift 2 ;;
    --db) TARGET_DB="${2:?--db requires a name}"; shift 2 ;;
    --create) DO_CREATE=1; shift ;;
    --clean) DO_CLEAN=1; shift ;;
    --jobs) JOBS="${2:?--jobs requires a number}"; shift 2 ;;
    --yes) ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (use --help)" ;;
  esac
done

require_tool pg_restore
require_tool psql

# Resolve connection by label.
if [[ "${LABEL}" == "vectors" ]]; then
  HOST="${ECS_VECTOR_PG_HOST}"; PORT="${ECS_VECTOR_PG_PORT}"
  USER="${ECS_VECTOR_PG_USER}"; PASS="${ECS_VECTOR_PG_PASSWORD}"
  DEFAULT_DB="${ECS_VECTOR_PG_DATABASE}"
else
  HOST="${ECS_REPO_PG_HOST}"; PORT="${ECS_REPO_PG_PORT}"
  USER="${ECS_REPO_PG_USER}"; PASS="${ECS_REPO_PG_PASSWORD}"
  DEFAULT_DB="${ECS_REPO_PG_DATABASE}"
fi
TARGET_DB="${TARGET_DB:-${DEFAULT_DB}}"

# Resolve the backup file.
if [[ "${MODE}" == "latest" ]]; then
  FILE="$(ls -1t "${BACKUP_DIR}"/ecs_"${LABEL}"_*.dump 2>/dev/null | head -n1 || true)"
  [[ -n "${FILE}" ]] || die "no backups found for label '${LABEL}' in ${BACKUP_DIR}"
fi
[[ -f "${FILE}" ]] || die "backup file not found: ${FILE}"

# Optional checksum verification.
if [[ -f "${FILE}.sha256" ]]; then
  log "Verifying checksum for $(basename "${FILE}")"
  if command -v sha256sum >/dev/null 2>&1; then
    ( cd "$(dirname "${FILE}")" && sha256sum -c "$(basename "${FILE}").sha256" ) >/dev/null \
      || die "checksum verification FAILED for ${FILE}"
  elif command -v shasum >/dev/null 2>&1; then
    ( cd "$(dirname "${FILE}")" && shasum -a 256 -c "$(basename "${FILE}").sha256" ) >/dev/null \
      || die "checksum verification FAILED for ${FILE}"
  fi
fi

# Archive must be parseable before we touch the target.
pg_restore --list "${FILE}" >/dev/null 2>&1 || die "not a valid pg_dump archive: ${FILE}"

log "Restore plan:"
log "  source : ${FILE}"
log "  target : $(describe_target "${HOST}" "${PORT}" "${TARGET_DB}" "${USER}")"
log "  clean  : ${DO_CLEAN}   create: ${DO_CREATE}   jobs: ${JOBS}"

if [[ "${ASSUME_YES}" -ne 1 ]]; then
  printf '[ecs-backup] This will restore into "%s". Type the database name to confirm: ' "${TARGET_DB}" >&2
  read -r _confirm
  [[ "${_confirm}" == "${TARGET_DB}" ]] || die "confirmation mismatch; aborting"
fi

export PGPASSWORD="${PASS}"

if [[ "${DO_CREATE}" -eq 1 ]]; then
  if ! psql --host="${HOST}" --port="${PORT}" --username="${USER}" --dbname=postgres \
        -tAc "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'" | grep -q 1; then
    log "Creating database ${TARGET_DB}"
    psql --host="${HOST}" --port="${PORT}" --username="${USER}" --dbname=postgres \
      -c "CREATE DATABASE \"${TARGET_DB}\"" || die "failed to create ${TARGET_DB}"
  fi
fi

RESTORE_ARGS=(--host="${HOST}" --port="${PORT}" --username="${USER}" --dbname="${TARGET_DB}"
              --no-owner --no-privileges --jobs="${JOBS}")
[[ "${DO_CLEAN}" -eq 1 ]] && RESTORE_ARGS+=(--clean --if-exists)

log "Restoring ..."
# pg_restore may emit non-fatal warnings (e.g. extension already exists); --exit-on-error
# is intentionally NOT set so a clean restore over an existing schema still completes.
pg_restore "${RESTORE_ARGS[@]}" "${FILE}" || log "pg_restore finished with warnings (review output)"

log "Restore complete into ${TARGET_DB}."
