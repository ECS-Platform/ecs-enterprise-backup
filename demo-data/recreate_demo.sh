#!/usr/bin/env bash
# ECS — single command to (re)create the entire demo environment from scratch.
#
#   ./demo-data/recreate_demo.sh
#
# Tears everything down (including volumes for a clean slate), brings the stack
# back up, seeds 6 demo applications across Gitea/Jenkins/SonarQube, triggers ECS
# evidence collection, and prints verification counts.
set -uo pipefail
cd "$(dirname "$0")/.."

echo "==================================================================="
echo " ECS demo recreate: down -v -> up -> seed -> sync -> verify"
echo "==================================================================="

echo "### [1/5] Tearing down (clean slate)..."
docker compose --profile sources --profile demo-connectors down -v

echo "### [2/5] Starting stack (platform + sources)..."
docker compose --profile sources --profile demo-connectors up -d

echo "### [3/5] Seeding demo data (this scans 6 projects; allow a few minutes)..."
./demo-data/seed_demo_environment.sh

echo "### [4/5] Wiring Gitea token into ECS and recreating the app..."
export GITEA_TOKEN="$(cat demo-data/.gitea_token 2>/dev/null || echo '')"
docker compose up -d ecs
# Give ECS a moment to reload + connect.
for i in $(seq 1 20); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 localhost:8000/api/platform/health)" = "200" ] && break
  sleep 3
done

echo "### [5/5] Triggering ECS evidence collection..."
for c in gitea jenkins sonarqube; do
  echo "  -> sync $c"
  curl -s -X POST "localhost:8000/api/platform/sync/$c" \
    | python3 -c 'import sys,json
d=json.load(sys.stdin)
print("     ok=%s collected=%s persisted=%s relationships=%s %s" % (
  d.get("ok"), d.get("collected"), d.get("persisted"), d.get("relationships"),
  ("warn:"+";".join(d.get("warnings",[]))) if d.get("warnings") else ""))' 2>/dev/null \
    || echo "     (sync call failed)"
done

echo
echo "=========================== VERIFY ==============================="
curl -s localhost:8000/api/platform/health | python3 -c 'import sys,json
d=json.load(sys.stdin)
print("total evidence :", d["counts"]["total"])
print("by source      :", json.dumps(d["counts"]["by_source"]))
print("by type        :", json.dumps(d["counts"].get("by_type",{})))'
curl -s localhost:8000/api/platform/evidence | python3 -c 'import sys,json
d=json.load(sys.stdin)
apps=sorted({r.get("application") for r in d.get("rows",[]) if r.get("application")})
print("relationship groups:", len(d.get("correlations",[])))
print("applications   :", ", ".join(apps))'
echo "=================================================================="
echo "UI:  http://localhost:8000/mvp/integration-health?role=admin&user=Admin"
echo "UI:  http://localhost:8000/mvp/evidence-explorer?role=admin&user=Admin"
