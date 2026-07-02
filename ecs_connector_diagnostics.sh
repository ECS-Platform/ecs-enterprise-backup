#!/bin/bash

OUTPUT="ecs_connector_diagnostics_$(date +%Y%m%d_%H%M%S).log"

docker info >/dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "Docker daemon is not running." >> "$OUTPUT"
    echo "Start Docker Desktop and rerun diagnostics."
    exit 1
fi


echo "==================================================" >> $OUTPUT
echo "ECS CONNECTOR DIAGNOSTICS REPORT" >> $OUTPUT
echo "Generated: $(date)" >> $OUTPUT
echo "==================================================" >> $OUTPUT

echo "" >> $OUTPUT
echo "########## DOCKER CONTAINERS ##########" >> $OUTPUT
docker ps -a >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## DOCKER IMAGES ##########" >> $OUTPUT
docker images >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## ECS CONTAINER ##########" >> $OUTPUT
docker ps --format "{{.Names}}" | grep ecs >> $OUTPUT 2>&1

ECS_CONTAINER=$(docker ps --format "{{.Names}}" | grep ecs | head -1)

echo "Detected ECS Container: $ECS_CONTAINER" >> $OUTPUT

echo "" >> $OUTPUT
echo "########## ECS LOGS ##########" >> $OUTPUT
docker logs $ECS_CONTAINER --tail 1000 >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## PYTHON PACKAGES ##########" >> $OUTPUT
docker exec $ECS_CONTAINER pip list >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## POSTGRES DRIVERS ##########" >> $OUTPUT
docker exec $ECS_CONTAINER pip list | grep -i psycopg >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## SONARQUBE ##########" >> $OUTPUT
docker ps -a | grep -i sonar >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## TRIVY ##########" >> $OUTPUT
docker ps -a | grep -i trivy >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## GITLEAKS ##########" >> $OUTPUT
docker images | grep -i gitleaks >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## ECS ENVIRONMENT ##########" >> $OUTPUT
docker exec $ECS_CONTAINER env >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## EXECUTION FAILURES ##########" >> $OUTPUT
docker logs $ECS_CONTAINER 2>&1 | grep -Ei \
"error|exception|traceback|connector|trivy|gitleaks|sonarqube|postgres|psycopg|dependency" \
>> $OUTPUT

echo "" >> $OUTPUT
echo "########## PREDEFINED QUERY FILES ##########" >> $OUTPUT

find . \
-type f \
\( -name "*.py" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) \
| grep -Ei "query|control|connector|execution" \
>> $OUTPUT

echo "" >> $OUTPUT
echo "########## APP-001 ##########" >> $OUTPUT
grep -R --exclude="ecs_connector_diagnostics*" --exclude="*.log" "APP-001" . >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## APP-002 ##########" >> $OUTPUT
grep -R --exclude="ecs_connector_diagnostics*" --exclude="*.log" "APP-002" . >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## APP-004 ##########" >> $OUTPUT
grep -R --exclude="ecs_connector_diagnostics*" --exclude="*.log" "APP-004" . >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## DB-001 ##########" >> $OUTPUT
grep -R --exclude="ecs_connector_diagnostics*" --exclude="*.log" "DB-001" . >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "########## OS-001 ##########" >> $OUTPUT
grep -R --exclude="ecs_connector_diagnostics*" --exclude="*.log" "OS-001" . >> $OUTPUT 2>&1

echo "" >> $OUTPUT
echo "Diagnostics complete."
echo "Output file: $OUTPUT"
