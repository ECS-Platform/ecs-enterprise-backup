#!/usr/bin/env bash
# Repeatable demo pipeline seeder for ECS:
#   Gitea repo + commits + PR  ->  Jenkins job + build  ->  SonarQube analysis
# All three use the SAME name (ecs-demo-app) so ECS correlates them into one
# Commit -> Build -> Sonar Scan chain (relationships are grouped by application).
#
# Prereqs (run once):
#   docker compose --profile sources up -d gitea jenkins
#   docker compose --profile demo-connectors up -d sonarqube-demo
#
# Usage:
#   ./demo-data/seed_pipeline_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

APP="ecs-demo-app"
GITEA=http://localhost:3000
JENKINS=http://localhost:8080
GADMIN_USER=ecsadmin
GADMIN_PASS=ecsadmin123

echo "############ 1) GITEA: admin + token + repo + commits ############"
# Admin user (idempotent — INSTALL_LOCK=true means API/CLI are available).
docker compose exec -T gitea gitea admin user create \
  --username "$GADMIN_USER" --password "$GADMIN_PASS" \
  --email ecsadmin@example.com --admin --must-change-password=false 2>/dev/null \
  || echo "  (admin user already exists)"

# Personal access token for ECS (read scopes are enough to collect evidence).
GITEA_TOKEN="$(curl -s -u "$GADMIN_USER:$GADMIN_PASS" -X POST \
  "$GITEA/api/v1/users/$GADMIN_USER/tokens" -H 'Content-Type: application/json' \
  -d '{"name":"ecs-demo-'"$RANDOM"'","scopes":["read:repository","read:user","read:organization"]}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("sha1",""))')"
echo "  GITEA_TOKEN=$GITEA_TOKEN"

# Repo with an initial commit.
curl -s -u "$GADMIN_USER:$GADMIN_PASS" -X POST "$GITEA/api/v1/user/repos" \
  -H 'Content-Type: application/json' \
  -d '{"name":"'"$APP"'","auto_init":true,"private":false,"default_branch":"main"}' >/dev/null || true

# A real source commit on main.
APP_B64="$(base64 < demo-data/sonar-demo/app.py | tr -d '\n')"
curl -s -u "$GADMIN_USER:$GADMIN_PASS" -X POST \
  "$GITEA/api/v1/repos/$GADMIN_USER/$APP/contents/app.py" -H 'Content-Type: application/json' \
  -d '{"content":"'"$APP_B64"'","message":"feat: add demo application","branch":"main"}' >/dev/null || true

# A feature branch + pull request (pull_request evidence).
curl -s -u "$GADMIN_USER:$GADMIN_PASS" -X POST \
  "$GITEA/api/v1/repos/$GADMIN_USER/$APP/contents/README.md" -H 'Content-Type: application/json' \
  -d '{"content":"'"$(printf 'ECS demo' | base64)"'","message":"docs: add readme","branch":"main","new_branch":"feature/readme"}' >/dev/null || true
curl -s -u "$GADMIN_USER:$GADMIN_PASS" -X POST \
  "$GITEA/api/v1/repos/$GADMIN_USER/$APP/pulls" -H 'Content-Type: application/json' \
  -d '{"head":"feature/readme","base":"main","title":"Add README"}' >/dev/null || true
echo "  Gitea repo '$APP' ready (commits + PR)."

echo "############ 2) JENKINS: job + build ############"
# Setup wizard is disabled (JAVA_OPTS) so anonymous has admin. Get a CSRF crumb.
CRUMB="$(curl -s "$JENKINS/crumbIssuer/api/json" \
  | python3 -c 'import sys,json
try:
  d=json.load(sys.stdin);print(d["crumbRequestField"]+":"+d["crumb"])
except Exception:
  print("")' 2>/dev/null || echo "")"
CRUMB_HDR=(); [ -n "$CRUMB" ] && CRUMB_HDR=(-H "$CRUMB")

# Minimal freestyle job that "builds" and runs a test step.
cat > /tmp/ecs_job.xml <<'XML'
<?xml version='1.1' encoding='UTF-8'?>
<project>
  <description>ECS demo pipeline job</description>
  <keepDependencies>false</keepDependencies>
  <scm class="hudson.scm.NullSCM"/>
  <canRoam>true</canRoam>
  <disabled>false</disabled>
  <triggers/>
  <builders>
    <hudson.tasks.Shell>
      <command>echo "Building ecs-demo-app"; echo "tests passed"</command>
    </hudson.tasks.Shell>
  </builders>
  <publishers/>
  <buildWrappers/>
</project>
XML
curl -s "${CRUMB_HDR[@]}" -X POST "$JENKINS/createItem?name=$APP" \
  -H 'Content-Type: application/xml' --data-binary @/tmp/ecs_job.xml >/dev/null || echo "  (job may already exist)"
curl -s "${CRUMB_HDR[@]}" -X POST "$JENKINS/job/$APP/build" >/dev/null || true
echo "  Jenkins job '$APP' created and build triggered."

echo "############ 3) SONARQUBE: project + scan ############"
PROJECT_KEY="$APP" PROJECT_NAME="$APP" ./demo-data/seed_sonarqube_demo.sh

echo
echo "############ DONE ############"
echo "Export the Gitea token and recreate ECS so the connector authenticates:"
echo "    export GITEA_TOKEN=$GITEA_TOKEN"
echo "    docker compose up -d ecs"
echo "Then trigger sync:  curl -s -X POST localhost:8000/api/platform/sync/gitea"
