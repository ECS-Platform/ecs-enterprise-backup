#!/usr/bin/env bash

# Repository
export ECS_REPO_PG_HOST=localhost
export ECS_REPO_PG_PORT=5433
export ECS_REPO_PG_DATABASE=ecs_repository
export ECS_REPO_PG_USER=ecs_user
export ECS_REPO_PG_PASSWORD=ecs_password

# PGVector
export ECS_VECTOR_PG_HOST=localhost
export ECS_VECTOR_PG_PORT=5434
export ECS_VECTOR_PG_PASSWORD=ecs_password

# Ollama
export ECS_LLM_PROVIDER=ollama
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=qwen3:8b

# Python
export PYTHONPATH=.

echo "✅ ECS benchmark environment loaded."