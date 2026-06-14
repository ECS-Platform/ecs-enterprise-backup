#!/usr/bin/env bash
# ECS backup/restore shared environment resolver (Phase 5 Step 1).
#
# Sourced by every backup/restore script. It resolves the SAME PostgreSQL
# connection settings ECS itself uses (config/repository.yaml -> ECS_REPO_PG_*),
# plus backup output/retention settings, with safe defaults. It loads a local .env
# if present so operators can run scripts the same way the app is configured.
#
# It NEVER prints secrets. Connection password is exported as PGPASSWORD only for the
# duration of a libpq tool invocation by the calling script.
#
# Scope: backup/restore/migration readiness only — no HA/DR/monitoring.

set -euo pipefail

# --- Resolve repo root and load .env (if any) without overriding the environment ---
_THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ECS_ROOT="$(cd "${_THIS_DIR}/../.." && pwd)"

if [[ -f "${ECS_ROOT}/.env" ]]; then
  # Export only KEY=VALUE lines; ignore comments/blank lines. Existing env wins.
  while IFS= read -r _line; do
    case "${_line}" in
      ''|\#*) continue ;;
    esac
    _key="${_line%%=*}"
    if [[ "${_key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] && [[ -z "${!_key:-}" ]]; then
      export "${_line?}"
    fi
  done < "${ECS_ROOT}/.env"
fi

# --- Evidence repository connection (mirrors config/repository.yaml defaults) ------
ECS_REPO_PG_HOST="${ECS_REPO_PG_HOST:-localhost}"
ECS_REPO_PG_PORT="${ECS_REPO_PG_PORT:-5432}"
ECS_REPO_PG_DATABASE="${ECS_REPO_PG_DATABASE:-ecs_repository}"
ECS_REPO_PG_USER="${ECS_REPO_PG_USER:-ecs_user}"
ECS_REPO_PG_PASSWORD="${ECS_REPO_PG_PASSWORD:-}"

# --- Optional vector store connection (config/vectorstore.yaml) --------------------
ECS_VECTOR_PG_HOST="${ECS_VECTOR_PG_HOST:-localhost}"
ECS_VECTOR_PG_PORT="${ECS_VECTOR_PG_PORT:-5432}"
ECS_VECTOR_PG_DATABASE="${ECS_VECTOR_PG_DATABASE:-ecs_vectors}"
ECS_VECTOR_PG_USER="${ECS_VECTOR_PG_USER:-ecs_user}"
ECS_VECTOR_PG_PASSWORD="${ECS_VECTOR_PG_PASSWORD:-}"

# --- Backup output + retention ----------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-${ECS_ROOT}/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

# Custom-format pg_dump is the canonical artifact (compressed, supports pg_restore
# selective/parallel restore). File naming: ecs_<db>_<UTC-timestamp>.dump
BACKUP_FORMAT="${BACKUP_FORMAT:-custom}"

log()  { printf '[ecs-backup] %s\n' "$*" >&2; }
err()  { printf '[ecs-backup][ERROR] %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }

require_tool() {
  command -v "$1" >/dev/null 2>&1 || die "required tool not found on PATH: $1"
}

timestamp() { date -u +%Y%m%dT%H%M%SZ; }

# Echo a single-line, secret-free summary of the target connection.
describe_target() {
  local host="$1" port="$2" db="$3" user="$4"
  printf '%s@%s:%s/%s' "${user}" "${host}" "${port}" "${db}"
}
