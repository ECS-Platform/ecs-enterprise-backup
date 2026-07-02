#!/usr/bin/env bash
# ECS demo data seeding utility (exec-free: uses curl + `docker run` only).
#
# Seeds 6 banking applications across the running Gitea, Jenkins and SonarQube
# instances. Each application uses the SAME slug across all three systems so ECS
# correlates evidence into one Commit -> Build -> Sonar Scan chain per app.
#
# Apps: mobile-banking net-banking upi payments treasury api-gateway
#
# Prereqs:
#   docker compose --profile sources up -d gitea jenkins
#   docker compose --profile demo-connectors up -d sonarqube-demo
#
# Usage:  ./demo-data/seed_demo_environment.sh
# Writes the generated Gitea token to demo-data/.gitea_token
set -uo pipefail
cd "$(dirname "$0")/.."

GITEA=http://localhost:3000
JENKINS=http://localhost:8080
SONAR=http://localhost:9000
SONAR_IN_NET=http://sonarqube-demo:9000
GUSER=ecsadmin; GPASS=ecsadmin123; GEMAIL=ecsadmin@example.com
SONAR_USER=admin; SONAR_PASS=a123
JUSER="${JENKINS_USER:-admin}"; JPASS="${JENKINS_TOKEN:-admin123}"
# Shared cookie jar keeps the (session-bound) Jenkins CSRF crumb valid for writes.
JCOOKIE="$(mktemp)"; trap 'rm -f "$JCOOKIE"' EXIT
JAUTH=(-u "$JUSER:$JPASS" -b "$JCOOKIE" -c "$JCOOKIE")
SCAN_DIR="$(cd demo-data/sonar-demo && pwd)"

APPS=(mobile-banking net-banking upi payments treasury api-gateway)

b64() { base64 < "$1" | tr -d '\n'; }
b64s() { printf '%s' "$1" | base64 | tr -d '\n'; }

echo "########## 0) Wait for services ##########"
for url in "$GITEA/" "$JENKINS/login" "$SONAR/api/system/status"; do
  for i in $(seq 1 40); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "$url" || echo 000)
    [ "$code" != "000" ] && break; sleep 3
  done
done
# SonarQube must report UP before it accepts analyses.
for i in $(seq 1 60); do
  st=$(curl -s "$SONAR/api/system/status" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status",""))' 2>/dev/null || echo "")
  [ "$st" = "UP" ] && break; echo "  waiting for SonarQube ($st)..."; sleep 5
done

echo "########## 1) GITEA install + admin (HTTP form, no exec) ##########"
if [ "$(curl -s -o /dev/null -w '%{http_code}' "$GITEA/api/v1/version")" != "200" ]; then
  curl -s -X POST "$GITEA/" \
    --data-urlencode "db_type=sqlite3" \
    --data-urlencode "db_path=/data/gitea/gitea.db" \
    --data-urlencode "app_name=ECS Gitea" \
    --data-urlencode "repo_root_path=/data/git/repositories" \
    --data-urlencode "lfs_root_path=/data/git/lfs" \
    --data-urlencode "run_user=git" \
    --data-urlencode "domain=localhost" \
    --data-urlencode "ssh_port=22" \
    --data-urlencode "http_port=3000" \
    --data-urlencode "app_url=http://localhost:3000/" \
    --data-urlencode "log_root_path=/data/gitea/log" \
    --data-urlencode "admin_name=$GUSER" \
    --data-urlencode "admin_passwd=$GPASS" \
    --data-urlencode "admin_confirm_passwd=$GPASS" \
    --data-urlencode "admin_email=$GEMAIL" >/dev/null
  echo "  submitted /install; waiting for API..."
  for i in $(seq 1 30); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' "$GITEA/api/v1/version")" = "200" ] && break; sleep 2
  done
fi
echo "  gitea version: $(curl -s "$GITEA/api/v1/version")"

# Fresh API token for ECS.
curl -s -u "$GUSER:$GPASS" -X DELETE "$GITEA/api/v1/users/$GUSER/tokens/ecs-demo" >/dev/null 2>&1 || true
GTOKEN="$(curl -s -u "$GUSER:$GPASS" -X POST "$GITEA/api/v1/users/$GUSER/tokens" \
  -H 'Content-Type: application/json' \
  -d '{"name":"ecs-demo","scopes":["read:repository","read:user","read:organization"]}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("sha1",""))')"
echo "$GTOKEN" > demo-data/.gitea_token
echo "  GITEA_TOKEN=$GTOKEN (saved to demo-data/.gitea_token)"

# Jenkins CSRF crumb (authenticated as admin; cookie jar keeps it valid for POSTs).
CRUMB="$(curl -s "${JAUTH[@]}" "$JENKINS/crumbIssuer/api/json" | python3 -c 'import sys,json
try: d=json.load(sys.stdin);print(d["crumbRequestField"]+":"+d["crumb"])
except Exception: print("")' 2>/dev/null || echo "")"
CRUMB_HDR=(); [ -n "$CRUMB" ] && CRUMB_HDR=(-H "$CRUMB")

# Detect compose network for the scanner container.
NET="$(docker network ls --format '{{.Name}}' | grep -E 'ecs.*default|default.*ecs' | head -1 || true)"
NET="${NET:-ecs_default}"
echo "  docker network for scanner: $NET"

# A fresh SonarQube defaults to admin/admin and forces a password change before
# its API is usable. Ensure the demo password ($SONAR_PASS) is in effect.
if ! curl -s -u "$SONAR_USER:$SONAR_PASS" "$SONAR/api/authentication/validate" | grep -q '"valid":true'; then
  echo "  [sonarqube] setting admin password to demo value"
  curl -s -u "admin:admin" -X POST \
    "$SONAR/api/users/change_password?login=admin&previousPassword=admin&password=$SONAR_PASS" >/dev/null || true
fi

APP_B64="$(b64 demo-data/sonar-demo/app.py)"
README_B64="$(b64s 'ECS demo application')"

for APP in "${APPS[@]}"; do
  echo "########## APP: $APP ##########"

  echo "  [gitea] repo + commits + PR"
  curl -s -u "$GUSER:$GPASS" -X POST "$GITEA/api/v1/user/repos" -H 'Content-Type: application/json' \
    -d '{"name":"'"$APP"'","auto_init":true,"private":false,"default_branch":"main"}' >/dev/null || true
  curl -s -u "$GUSER:$GPASS" -X POST "$GITEA/api/v1/repos/$GUSER/$APP/contents/app.py" \
    -H 'Content-Type: application/json' \
    -d '{"content":"'"$APP_B64"'","message":"feat: add application code","branch":"main"}' >/dev/null || true
  curl -s -u "$GUSER:$GPASS" -X POST "$GITEA/api/v1/repos/$GUSER/$APP/contents/CHANGELOG.md" \
    -H 'Content-Type: application/json' \
    -d '{"content":"'"$README_B64"'","message":"chore: changelog","branch":"main"}' >/dev/null || true
  curl -s -u "$GUSER:$GPASS" -X POST "$GITEA/api/v1/repos/$GUSER/$APP/contents/README.md" \
    -H 'Content-Type: application/json' \
    -d '{"content":"'"$README_B64"'","message":"docs: readme","branch":"main","new_branch":"feature/readme"}' >/dev/null || true
  curl -s -u "$GUSER:$GPASS" -X POST "$GITEA/api/v1/repos/$GUSER/$APP/pulls" \
    -H 'Content-Type: application/json' \
    -d '{"head":"feature/readme","base":"main","title":"Add README for '"$APP"'"}' >/dev/null || true

  echo "  [jenkins] job + build"
  printf '<?xml version="1.1" encoding="UTF-8"?>\n<project><description>ECS demo: %s</description><keepDependencies>false</keepDependencies><scm class="hudson.scm.NullSCM"/><canRoam>true</canRoam><disabled>false</disabled><triggers/><builders><hudson.tasks.Shell><command>echo building %s; echo tests passed</command></hudson.tasks.Shell></builders><publishers/><buildWrappers/></project>\n' "$APP" "$APP" > /tmp/job_$APP.xml
  curl -s "${JAUTH[@]}" ${CRUMB_HDR[@]+"${CRUMB_HDR[@]}"} -X POST "$JENKINS/createItem?name=$APP" \
    -H 'Content-Type: application/xml' --data-binary @/tmp/job_$APP.xml >/dev/null || true
  curl -s "${JAUTH[@]}" ${CRUMB_HDR[@]+"${CRUMB_HDR[@]}"} -X POST "$JENKINS/job/$APP/build" >/dev/null || true

  echo "  [sonarqube] project + scan"
  curl -s -u "$SONAR_USER:$SONAR_PASS" -X POST \
    "$SONAR/api/projects/create?project=$APP&name=$APP" >/dev/null || true
  curl -s -u "$SONAR_USER:$SONAR_PASS" -X POST "$SONAR/api/user_tokens/revoke?name=scan-$APP" >/dev/null || true
  STOKEN="$(curl -s -u "$SONAR_USER:$SONAR_PASS" -X POST "$SONAR/api/user_tokens/generate?name=scan-$APP" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')"
  # SonarQube 9.9 expects the token in sonar.login (sonar.token is 10.x+).
  docker run --rm --network "$NET" -v "$SCAN_DIR:/usr/src" sonarsource/sonar-scanner-cli \
    -Dsonar.host.url="$SONAR_IN_NET" -Dsonar.login="$STOKEN" \
    -Dsonar.projectKey="$APP" -Dsonar.projectName="$APP" >/dev/null 2>&1 \
    && echo "    scan submitted" || echo "    scan FAILED for $APP (check scanner/network)"
done

echo
echo "########## SEED COMPLETE ##########"
echo "Apps seeded: ${APPS[*]}"
echo "Next: export GITEA_TOKEN=\$(cat demo-data/.gitea_token) && docker compose up -d ecs"
