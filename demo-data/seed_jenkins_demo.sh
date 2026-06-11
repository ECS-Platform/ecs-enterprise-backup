#!/usr/bin/env bash
# ECS Jenkins demo pipeline (exec-free: curl only).
#
#   ./demo-data/seed_jenkins_demo.sh
#
# 1) creates the freestyle job "mobile-banking-build"
# 2) the job generates sample source, builds it, archives artifacts
# 3) executes a build and waits for completion
# 4) prints the stored build metadata
# 5) triggers ECS evidence collection for the jenkins connector
# 6) verifies the evidence appears in the repository (Evidence Explorer source=jenkins)
#
# Requires the jenkins service running:  docker compose --profile sources up -d jenkins
set -uo pipefail
cd "$(dirname "$0")/.."

JENKINS=http://localhost:8080
ECS=http://localhost:8000
JUSER="${JENKINS_USER:-admin}"
JPASS="${JENKINS_TOKEN:-admin123}"
JOB=mobile-banking-build
CFG=demo-data/jenkins/mobile-banking-build.config.xml
# Shared cookie jar so the CSRF crumb (session-bound) stays valid across POSTs.
COOKIE="$(mktemp)"; trap 'rm -f "$COOKIE"' EXIT
AUTH=(-u "$JUSER:$JPASS" -b "$COOKIE" -c "$COOKIE")

echo "########## 0) Wait for Jenkins (authenticated) ##########"
ready=""
for i in $(seq 1 60); do
  code=$(curl -s -g "${AUTH[@]}" -o /dev/null -w '%{http_code}' --max-time 5 "$JENKINS/api/json" || echo 000)
  if [ "$code" = "200" ]; then ready=1; echo "  Jenkins ready (HTTP 200)"; break; fi
  echo "  waiting for Jenkins... (HTTP $code)"; sleep 3
done
if [ -z "$ready" ]; then
  echo "ERROR: Jenkins not reachable/authenticated at $JENKINS as $JUSER."
  echo "  Recreate it so the init script runs:  docker compose --profile sources up -d --force-recreate jenkins"
  exit 1
fi

# CSRF crumb (required for POST). Basic auth is reused on every call.
CRUMB="$(curl -s -g "${AUTH[@]}" "$JENKINS/crumbIssuer/api/json" \
  | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d["crumbRequestField"]+":"+d["crumb"])
except Exception:
    print("")' 2>/dev/null || echo "")"
CRUMB_HDR=(); [ -n "$CRUMB" ] && CRUMB_HDR=(-H "$CRUMB")
echo "  crumb: ${CRUMB:-<none>}"

echo "########## 1+2) Create/update job $JOB ##########"
if [ "$(curl -s -g "${AUTH[@]}" -o /dev/null -w '%{http_code}' "$JENKINS/job/$JOB/api/json")" = "200" ]; then
  echo "  job exists -> updating config.xml"
  curl -s -g "${AUTH[@]}" "${CRUMB_HDR[@]}" -X POST "$JENKINS/job/$JOB/config.xml" \
    -H 'Content-Type: application/xml' --data-binary @"$CFG" >/dev/null
else
  echo "  creating job"
  curl -s -g "${AUTH[@]}" "${CRUMB_HDR[@]}" -X POST "$JENKINS/createItem?name=$JOB" \
    -H 'Content-Type: application/xml' --data-binary @"$CFG" >/dev/null
fi
echo "  job present: $(curl -s -g "${AUTH[@]}" -o /dev/null -w '%{http_code}' "$JENKINS/job/$JOB/api/json")"

echo "########## 3) Execute build ##########"
LAST_BEFORE="$(curl -s -g "${AUTH[@]}" "$JENKINS/job/$JOB/api/json?tree=lastBuild[number]" \
  | python3 -c 'import sys,json;print((json.load(sys.stdin).get("lastBuild") or {}).get("number") or 0)' 2>/dev/null || echo 0)"
curl -s -g "${AUTH[@]}" "${CRUMB_HDR[@]}" -X POST "$JENKINS/job/$JOB/build" >/dev/null
echo "  build triggered (previous build #: $LAST_BEFORE); waiting for completion..."

RESULT=""; NUM=""
for i in $(seq 1 60); do
  read -r NUM RESULT < <(curl -s -g "${AUTH[@]}" \
    "$JENKINS/job/$JOB/lastBuild/api/json?tree=number,result" \
    | python3 -c 'import sys,json
d=json.load(sys.stdin); print(d.get("number") or "", d.get("result") or "")' 2>/dev/null || echo " ")
  if [ -n "$NUM" ] && [ "$NUM" != "$LAST_BEFORE" ] && [ -n "$RESULT" ]; then break; fi
  sleep 2
done
echo "  build #$NUM finished: ${RESULT:-UNKNOWN}"

echo "########## 4) Stored build metadata ##########"
curl -s -g "${AUTH[@]}" \
  "$JENKINS/job/$JOB/lastBuild/api/json?tree=number,result,timestamp,duration,url,builtOn,artifacts[fileName]" \
  | python3 -m json.tool || true

echo "########## 5) Trigger ECS sync (jenkins) ##########"
curl -s -X POST "$ECS/api/platform/sync/jenkins" | python3 -c 'import sys,json
d=json.load(sys.stdin)
print("  ok=%s collected=%s persisted=%s relationships=%s indexed=%s %s" % (
  d.get("ok"), d.get("collected"), d.get("persisted"), d.get("relationships"), d.get("indexed"),
  ("error:"+d.get("error","")) if not d.get("ok") else ""))' 2>/dev/null \
  || echo "  (sync call failed; is ECS up at $ECS?)"

echo "########## 6) Verify evidence in repository (source=jenkins) ##########"
curl -s "$ECS/api/platform/evidence?source_system=jenkins" | python3 -c 'import sys,json
d=json.load(sys.stdin)
rows=d.get("rows",[])
print("  jenkins evidence rows:", len(rows))
for r in rows[:10]:
    print("   -", r.get("object_type"), "|", r.get("title"), "| app:", r.get("application"))'  2>/dev/null \
  || echo "  (evidence query failed)"

echo
echo "Done. View in the UI:"
echo "  $ECS/mvp/evidence-explorer?role=admin&user=Admin   (click the 'jenkins' quick filter)"
echo "  $ECS/mvp/integration-health?role=admin&user=Admin"
