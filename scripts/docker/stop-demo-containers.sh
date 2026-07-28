#!/usr/bin/env bash

KEEP=(
  "ecs-enterprise-backup-postgres-1"
  "ecs-enterprise-backup-pgvector-1"
  "ecs-enterprise-backup-minio-1"
  "ecs-enterprise-backup-redis-1"
)

for c in $(docker ps --format "{{.Names}}"); do
  if [[ ! " ${KEEP[*]} " =~ " ${c} " ]]; then
    echo "Stopping $c..."
    docker stop "$c"
  fi
done

echo
docker ps --format "table {{.Names}}\t{{.Status}}"
