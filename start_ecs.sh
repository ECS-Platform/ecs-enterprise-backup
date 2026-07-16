#!/bin/bash
# ECS root startup — interactive menu + non-interactive flags.
#
#   ./start_ecs.sh            # interactive menu
#   ./start_ecs.sh --demo     # demo mode (scripts/start_ecs_demo.sh --all --skip-heavy)
#   ./start_ecs.sh --run      # normal run / development mode (Uvicorn)
#   ./start_ecs.sh --status   # basic ECS status (read-only)
#   ./start_ecs.sh --help     # usage
#
# Interactive and non-interactive modes call the SAME internal functions.
# Targeted ECS process/port handling only: no broad process sweeps and no
# compose teardown. Only confirmed ECS host processes / the ECS container are
# ever stopped; unrelated processes are reported, never terminated.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# The exact ECS Uvicorn target this launcher owns. Both `uvicorn app.main:app`
# and `python -m uvicorn app.main:app` contain this substring; unrelated uvicorn
# apps (a different :app) do not.
ECS_UVICORN_TARGET="uvicorn app.main:app"
ECS_PORT=8000

# --------------------------------------------------------------------------- #
# Identification helpers (read-only)
# --------------------------------------------------------------------------- #

# Full command line for a PID (empty if gone).
_pid_cmd() {
  ps -p "$1" -o command= 2>/dev/null | sed 's/^[[:space:]]*//'
}

# True if a PID's command is the exact ECS Uvicorn target (not this script, not
# a docker CLI line that merely mentions it).
_pid_is_ecs_uvicorn() {
  local pid="$1" cmd
  cmd="$(_pid_cmd "$pid")"
  [ -n "$cmd" ] || return 1
  case "$cmd" in
    *"$ECS_UVICORN_TARGET"*)
      case "$cmd" in
        *docker*|*start_ecs.sh*) return 1 ;;   # never match the CLI/this script
        *) return 0 ;;
      esac
      ;;
    *) return 1 ;;
  esac
}

# Host PIDs running the exact ECS Uvicorn target (space-separated, may be empty).
_ecs_uvicorn_pids() {
  local pids="" p
  # pgrep -f matches the full arg list; we then re-verify each PID exactly.
  for p in $(pgrep -f "$ECS_UVICORN_TARGET" 2>/dev/null); do
    if _pid_is_ecs_uvicorn "$p"; then
      pids="$pids $p"
    fi
  done
  echo "${pids# }"
}

# PID that currently LISTENS on the ECS port (empty if none).
_port_owner_pid() {
  lsof -nP "-iTCP:${ECS_PORT}" -sTCP:LISTEN -t 2>/dev/null | head -n1
}

# Docker Compose ECS application container name (empty if not running).
# Read-only detection: matches the compose service `ecs` / a name ending -ecs-1.
_docker_ecs_container() {
  command -v docker >/dev/null 2>&1 || return 0
  docker ps --filter "name=ecs" --format '{{.Names}}' 2>/dev/null \
    | grep -E '(^|[-_])ecs([-_]1)?$|-ecs-1$' | head -n1
}

# /healthz probe → prints "ok" (HTTP 200), "down", or "unknown".
_healthz() {
  if command -v curl >/dev/null 2>&1; then
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${ECS_PORT}/healthz" 2>/dev/null)"
    [ "$code" = "200" ] && { echo "ok"; return; }
    [ -n "$code" ] && { echo "down"; return; }
    echo "unknown"; return
  fi
  echo "unknown"
}

# Classify the ECS runtime on the port: docker | host-python | none | conflict.
_classify_runtime() {
  local container port_pid
  container="$(_docker_ecs_container)"
  port_pid="$(_port_owner_pid)"
  if [ -n "$container" ]; then
    echo "docker"; return
  fi
  if [ -z "$port_pid" ]; then
    echo "none"; return
  fi
  if _pid_is_ecs_uvicorn "$port_pid"; then
    echo "host-python"; return
  fi
  echo "conflict"
}

# Print "unrelated process owns :8000" details and return 0 if it IS a conflict
# (an owner that is not an ECS uvicorn and not the docker ECS container path).
_report_port_conflict() {
  local port_pid
  port_pid="$(_port_owner_pid)"
  [ -n "$port_pid" ] || return 1
  if _pid_is_ecs_uvicorn "$port_pid"; then
    return 1   # it's our ECS host process, not a conflict
  fi
  echo "Port ${ECS_PORT} is owned by an unrelated process — not killing it."
  echo "  PID: ${port_pid}"
  echo "  CMD: $(_pid_cmd "$port_pid")"
  return 0
}

# Send SIGTERM, wait for exit, SIGKILL only if still alive.
_graceful_stop_pid() {
  local pid="$1"
  [ -n "$pid" ] || return 0
  kill -TERM "$pid" 2>/dev/null || return 0
  local i=0
  while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 15 ]; do
    sleep 1
    i=$((i + 1))
  done
  if kill -0 "$pid" 2>/dev/null; then
    echo "PID ${pid} did not exit; sending SIGKILL…"
    kill -KILL "$pid" 2>/dev/null
    sleep 1
  fi
}

# Wait until nothing listens on the ECS port (up to 15s).
_wait_port_free() {
  local i=0
  while [ -n "$(_port_owner_pid)" ] && [ "$i" -lt 15 ]; do
    sleep 1
    i=$((i + 1))
  done
  [ -z "$(_port_owner_pid)" ]
}

# Stop only confirmed ECS host Uvicorn PIDs (targeted TERM). Never broad kill.
# Optional arg: a PID to KEEP (used to preserve one healthy instance).
_stop_ecs_uvicorn() {
  local keep="${1:-}" p stopped=""
  for p in $(_ecs_uvicorn_pids); do
    [ -n "$keep" ] && [ "$p" = "$keep" ] && continue
    kill "$p" 2>/dev/null && stopped="$stopped $p"
  done
  [ -n "$stopped" ] && echo "Stopped ECS host uvicorn:${stopped}"
  return 0
}

# Stop only the Docker ECS application container via `docker stop` (never other
# services/volumes; no compose teardown).
_stop_docker_ecs() {
  local container
  container="$(_docker_ecs_container)"
  [ -n "$container" ] || return 0
  docker stop "$container" >/dev/null 2>&1 && echo "Stopped Docker ECS container: ${container}"
  return 0
}

# --------------------------------------------------------------------------- #
# D: Demo mode
# --------------------------------------------------------------------------- #
run_demo() {
  # 1-2. Stop only confirmed ECS host Uvicorn processes (so the demo's Docker
  #      ECS is the single runtime). Never touches unrelated processes.
  _stop_ecs_uvicorn
  # 3. Detect the Docker Compose ECS container (report only; the demo script
  #    manages it).
  local container
  container="$(_docker_ecs_container)"
  [ -n "$container" ] && echo "Docker ECS container detected: ${container}"
  # 4-5. Inspect port 8000; an unrelated owner blocks the demo (do not kill it).
  if _report_port_conflict; then
    exit 1
  fi
  # 6. Never invoke Uvicorn in demo mode — delegate to the demo orchestrator.
  ./scripts/start_ecs_demo.sh --all --skip-heavy
}

# --------------------------------------------------------------------------- #
# R: Normal run / development mode
# --------------------------------------------------------------------------- #

# True only if the ECS Python deps are importable in the chosen interpreter.
_deps_present() {
  "$1" -c 'import fastapi, uvicorn, jinja2, multipart' >/dev/null 2>&1
}

run_normal() {
  # 1-2. Stop only the Docker ECS container (leave PostgreSQL/Redis/MinIO/demo
  #      targets/connector containers/volumes untouched).
  _stop_docker_ecs

  # 6. An unrelated process on :8000 blocks a host run (do not kill it).
  if _report_port_conflict; then
    exit 1
  fi

  # 3-5. If ECS already owns :8000, stop it gracefully and restart fresh.
  local pids port_pid
  pids="$(_ecs_uvicorn_pids)"
  port_pid="$(_port_owner_pid)"
  if [ -n "$port_pid" ] && _pid_is_ecs_uvicorn "$port_pid"; then
    echo "ECS on :${ECS_PORT} (PID ${port_pid}) — stopping for restart…"
    _graceful_stop_pid "$port_pid"
    if ! _wait_port_free; then
      port_pid="$(_port_owner_pid)"
      if [ -n "$port_pid" ] && _pid_is_ecs_uvicorn "$port_pid"; then
        _graceful_stop_pid "$port_pid"
      fi
      _wait_port_free || { echo "ERROR: port ${ECS_PORT} still in use." >&2; exit 1; }
    fi
    echo "Port ${ECS_PORT} is free."
  elif [ -n "$pids" ]; then
    echo "Stopping stray ECS uvicorn process(es)…"
    for p in $pids; do
      _graceful_stop_pid "$p"
    done
    _wait_port_free || true
  fi

  # 7. Prefer the venv interpreter's `-m uvicorn`; else the existing fallback.
  # 8. Install deps only if genuinely missing (prefer a clear error over
  #    reinstalling on every startup).
  echo "Starting ECS on :${ECS_PORT} (logs below)…"
  (sleep 3 && open "http://127.0.0.1:${ECS_PORT}" 2>/dev/null) &
  if [ -x ".venv/bin/python" ]; then
    if ! _deps_present ".venv/bin/python"; then
      echo "ECS dependencies missing in .venv — installing once…"
      .venv/bin/python -m pip install fastapi uvicorn jinja2 python-multipart || {
        echo "ERROR: failed to install ECS dependencies in .venv." >&2; exit 1; }
    fi
    exec .venv/bin/python -m uvicorn app.main:app --reload
  else
    # Existing valid fallback (no venv): use uvicorn on PATH.
    if ! command -v uvicorn >/dev/null 2>&1; then
      echo "ECS dependencies missing — installing once…"
      pip install fastapi uvicorn jinja2 python-multipart || {
        echo "ERROR: failed to install ECS dependencies." >&2; exit 1; }
    fi
    exec uvicorn app.main:app --reload
  fi
}

# --------------------------------------------------------------------------- #
# S: Status (read-only — never changes anything)
# --------------------------------------------------------------------------- #
run_status() {
  local runtime container pids port_pid health
  runtime="$(_classify_runtime)"
  container="$(_docker_ecs_container)"
  pids="$(_ecs_uvicorn_pids)"
  port_pid="$(_port_owner_pid)"
  health="$(_healthz)"

  echo "ECS Status"
  echo "  runtime:              ${runtime}"     # docker | host-python | none | conflict
  if [ -n "$container" ]; then
    echo "  docker ECS container: ${container} ($(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo unknown))"
  else
    echo "  docker ECS container: none"
  fi
  echo "  host ECS PID(s):      ${pids:-none}"
  if [ -n "$port_pid" ]; then
    echo "  port ${ECS_PORT} owner:      PID ${port_pid} — $(_pid_cmd "$port_pid")"
  else
    echo "  port ${ECS_PORT} owner:      none"
  fi
  echo "  /healthz:             ${health}"
}

# --------------------------------------------------------------------------- #
# Help + menu
# --------------------------------------------------------------------------- #
show_help() {
  cat <<'EOF'
ECS Startup

Usage:
  ./start_ecs.sh            Interactive menu
  ./start_ecs.sh --demo     Demo mode (scripts/start_ecs_demo.sh --all --skip-heavy)
  ./start_ecs.sh --run      Normal run / development mode (Uvicorn)
  ./start_ecs.sh --status   Show current basic ECS status (read-only)
  ./start_ecs.sh --help     Show this help
EOF
}

show_menu() {
  cat <<'EOF'
ECS Startup

[D] Demo mode
[R] Normal run / development mode
[S] Status
[Q] Quit

Enter option:
EOF
}

interactive_menu() {
  show_menu
  read -r choice
  case "${choice}" in
    D|d) run_demo ;;
    R|r) run_normal ;;
    S|s) run_status ;;
    Q|q) exit 0 ;;
    *) echo "Invalid option: ${choice}"; exit 1 ;;
  esac
}

# --- Dispatch (interactive + non-interactive call the SAME functions) -------
case "${1:-}" in
  --demo)   run_demo ;;
  --run)    run_normal ;;
  --status) run_status ;;
  --help|-h) show_help ;;
  "")       interactive_menu ;;
  *) echo "Unknown option: ${1}"; show_help; exit 1 ;;
esac
