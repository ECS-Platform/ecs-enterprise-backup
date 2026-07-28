#!/bin/bash
# ECS root startup — interactive menu + non-interactive flags.
#
#   ./start_ecs.sh            # interactive menu
#   ./start_ecs.sh --demo     # demo mode (Docker deps only + local Uvicorn)
#   ./start_ecs.sh --llm      # LLM demo / low memory (lightweight infra + local Uvicorn)
#   ./start_ecs.sh --run      # normal run / development mode (core infra + local Uvicorn)
#   ./start_ecs.sh --status   # basic ECS status (read-only)
#   ./start_ecs.sh --help     # usage
#
# Interactive and non-interactive modes call the SAME internal functions.
# Targeted ECS process/port handling only: no broad process sweeps and no
# compose teardown. Only confirmed ECS host processes / the ECS container are
# ever stopped; unrelated processes are reported, never terminated.
#
# Demo (D), Low Memory (L), and Normal Run (R) use Docker ONLY for infrastructure.
# The ECS FastAPI application always runs locally via uvicorn in this shell
# (never the compose `ecs` / ecs-enterprise-backup-ecs-1 container).

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
# L: LLM demo / low memory (lightweight compose stack — no PQ/demo targets)
# --------------------------------------------------------------------------- #
# Backing services required by ecs for repository, vectors, cache, and objects.
# The compose `ecs` app container is never started here — local uvicorn owns the app.
LLM_DEMO_BACKING_SERVICES=(postgres pgvector redis minio)

# Shared host-app path used by L / R after infrastructure is up (and mirrors
# Demo mode's post-infra steps). Stops a prior compose `ecs` container, frees
# :8000 when we own it, then exec's local uvicorn via `_launch_host_uvicorn`.
_start_local_ecs_app() {
  _stop_docker_ecs

  if _report_port_conflict; then
    exit 1
  fi

  _prepare_host_port_for_uvicorn

  # Foreground local app — exits when uvicorn exits (Ctrl+C clean shutdown).
  _launch_host_uvicorn --host 0.0.0.0 --port "${ECS_PORT}" --reload
}

run_llm_demo() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker not found." >&2
    exit 1
  fi

  echo ""
  echo "LLM Demo / Low Memory — starting lightweight stack only:"
  printf '  %s\n' "${LLM_DEMO_BACKING_SERVICES[@]}"
  echo "  ECS app: local uvicorn (compose service 'ecs' is NOT started)"
  echo "  (PQ/demo targets are NOT started: postgres-demo, sonarqube-demo, oracle-demo,"
  echo "   mongodb-demo, mysql-demo, apache/nginx/tomcat demos, rhel/ubuntu demos, aerospike)"
  echo ""
  echo "NOTE: Ollama runs natively on macOS — it is NOT started from Docker Compose."
  echo "      For LLM / RAG testing, run separately: ollama serve"
  echo ""

  # Backing services only — do not pull in depends_on demo targets or start `ecs`.
  docker compose up -d "${LLM_DEMO_BACKING_SERVICES[@]}"

  echo ""
  echo "Infrastructure ready → launching local ECS uvicorn on http://127.0.0.1:${ECS_PORT}"
  _start_local_ecs_app
}

# True only if the ECS Python deps are importable in the chosen interpreter.
_deps_present() {
  "$1" -c 'import fastapi, uvicorn, jinja2, multipart' >/dev/null 2>&1
}

# Prefer venv python when present (Unix or Windows Git Bash layout).
_python_bin() {
  if [ -x ".venv/bin/python" ]; then
    echo ".venv/bin/python"
  elif [ -x ".venv/Scripts/python.exe" ]; then
    echo ".venv/Scripts/python.exe"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo "python3"
  fi
}

# Free :8000 when an ECS host uvicorn already owns it (shared by demo + normal).
_prepare_host_port_for_uvicorn() {
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
}

# Start compose dependency/demo services for --all --skip-heavy, excluding `ecs`.
# Reuses scripts/ecs_demo_startup.py helpers (no duplicated service lists) and
# prints the same technology status table used by the demo orchestrator.
_start_demo_dependencies() {
  local py
  py="$(_python_bin)"
  echo "Starting Docker dependency services (excluding compose service 'ecs')…"
  PYTHONPATH="${SCRIPT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" "$py" - <<'PY'
from __future__ import annotations

import sys

from scripts.check_predefined_db_environment import load_env
from scripts.ecs_demo_startup import (
    CORE_SERVICES,
    ECS_SERVICE,
    build_rows,
    compose_config_valid,
    compose_up,
    detect_port_conflicts,
    docker_available,
    ecs_runtime,
    load_compose_services,
    parse_args,
    print_table,
    services_for_mode,
    TECHNOLOGY_SPECS,
    wait_core_backing,
)

print(f"[demo] env: {load_env()}")
if not docker_available():
    print("ERROR: Docker Desktop/daemon is not available. Start Docker and retry.", file=sys.stderr)
    raise SystemExit(1)

ok, msg = compose_config_valid()
if not ok:
    print(f"ERROR: docker compose config invalid: {msg}", file=sys.stderr)
    raise SystemExit(1)

args = parse_args(["--all", "--skip-heavy"])
services, profiles = services_for_mode(args)
services.discard(ECS_SERVICE)
to_start = set(CORE_SERVICES) | (services - set(CORE_SERVICES))
print(
    "[demo] dependency services: "
    + (", ".join(sorted(to_start)) if to_start else "(none)")
)
compose_up(to_start, profiles)
failures = wait_core_backing(args.wait_timeout)
if failures:
    for item in failures:
        print(f"CORE FAILURE: {item}", file=sys.stderr)
    raise SystemExit(1)
print("[demo] core backing services are healthy")

conflicts = detect_port_conflicts(list(TECHNOLOGY_SPECS), load_compose_services())
for msg in conflicts:
    print(f"WARNING: port conflict: {msg}")
print(f"ECS runtime: {ecs_runtime()} (app will start via local uvicorn)")
print_table(build_rows(to_start, wait=True, probe_connectors=False, port_conflicts=conflicts))
raise SystemExit(0)
PY
}

# Launch host uvicorn in the foreground. Extra flags are forwarded as-is.
# Uses exec so when uvicorn exits, this script exits with the same status.
_launch_host_uvicorn() {
  echo "Starting ECS on :${ECS_PORT} (logs below)…"
  if [ -x ".venv/bin/python" ]; then
    if ! _deps_present ".venv/bin/python"; then
      echo "ECS dependencies missing in .venv — installing once…"
      .venv/bin/python -m pip install fastapi uvicorn jinja2 python-multipart || {
        echo "ERROR: failed to install ECS dependencies in .venv." >&2; exit 1; }
    fi
    exec .venv/bin/python -m uvicorn app.main:app "$@"
  else
    if ! command -v uvicorn >/dev/null 2>&1; then
      echo "ECS dependencies missing — installing once…"
      pip install fastapi uvicorn jinja2 python-multipart || {
        echo "ERROR: failed to install ECS dependencies." >&2; exit 1; }
    fi
    exec uvicorn app.main:app "$@"
  fi
}

# --------------------------------------------------------------------------- #
# D: Demo mode — Docker deps only; local uvicorn for the ECS app
# --------------------------------------------------------------------------- #
run_demo() {
  echo "Demo mode: Docker for infrastructure/demo services only; ECS app via local uvicorn."

  # Stop any existing compose ECS application container (do not restart it).
  _stop_docker_ecs

  # Unrelated owner of :8000 blocks the host run (do not kill it).
  if _report_port_conflict; then
    exit 1
  fi

  # Free :8000 if a previous host ECS uvicorn is still bound.
  _prepare_host_port_for_uvicorn

  # Start dependency containers only (never compose service `ecs`) and print
  # the demo technology status / diagnostics table.
  if ! _start_demo_dependencies; then
    exit 1
  fi

  # Match docker ecs service defaults when unset; .env / process env still win.
  export DEMO_MODE="${DEMO_MODE:-true}"
  export ECS_AUTH_ENABLED="${ECS_AUTH_ENABLED:-false}"

  # Foreground local app — exits when uvicorn exits.
  _launch_host_uvicorn --host 0.0.0.0 --port "${ECS_PORT}" --reload
}

# --------------------------------------------------------------------------- #
# R: Normal run / development mode
# --------------------------------------------------------------------------- #
# Core ECS backing services (no heavy connector/demo OS targets). Compose `ecs`
# is never started — local uvicorn owns the app (same as Demo / Low Memory).
NORMAL_BACKING_SERVICES=(postgres-demo postgres pgvector redis minio)

run_normal() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker not found." >&2
    exit 1
  fi

  echo ""
  echo "Normal run / development — starting ECS infrastructure:"
  printf '  %s\n' "${NORMAL_BACKING_SERVICES[@]}"
  echo "  ECS app: local uvicorn (compose service 'ecs' is NOT started)"
  echo ""

  docker compose up -d "${NORMAL_BACKING_SERVICES[@]}"

  echo ""
  echo "Infrastructure ready → launching local ECS uvicorn on http://127.0.0.1:${ECS_PORT}"
  (sleep 3 && open "http://127.0.0.1:${ECS_PORT}" 2>/dev/null) &
  _start_local_ecs_app
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
  ./start_ecs.sh --demo     Demo mode (Docker deps only + local Uvicorn)
  ./start_ecs.sh --llm      LLM demo / low memory (postgres, pgvector, redis, minio + local Uvicorn)
  ./start_ecs.sh --run      Normal run / development mode (core infra + local Uvicorn)
  ./start_ecs.sh --status   Show current basic ECS status (read-only)
  ./start_ecs.sh --help     Show this help

All modes start Docker infrastructure only and run the FastAPI app locally via:
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
The compose `ecs` application container is never started by this script.
EOF
}

show_menu() {
  cat <<'EOF'
ECS Startup

[D] Demo mode
[L] LLM Demo / Low Memory
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
    L|l) run_llm_demo ;;
    R|r) run_normal ;;
    S|s) run_status ;;
    Q|q) exit 0 ;;
    *) echo "Invalid option: ${choice}"; exit 1 ;;
  esac
}

# --- Dispatch (interactive + non-interactive call the SAME functions) -------
case "${1:-}" in
  --demo)   run_demo ;;
  --llm)    run_llm_demo ;;
  --run)    run_normal ;;
  --status) run_status ;;
  --help|-h) show_help ;;
  "")       interactive_menu ;;
  *) echo "Unknown option: ${1}"; show_help; exit 1 ;;
esac
