# Changelog

All notable, milestone-level changes to the Evidence Collection System (ECS) are
documented here. The most recent milestone appears at the top.

Format is loosely based on [Keep a Changelog](https://keepachangelog.com/).

---

## ecs-predefined-db-complete-v1

Released: 2026-07-06

### Summary

Completed ECS Predefined Database Query Module Version 1.

This milestone adds live predefined database query support for PostgreSQL, YugabyteDB, and Aurora MySQL-compatible MySQL, including backend connectors, supplementary query catalog, frontend Run Query integration, technology filtering, onboarding diagnostics, and developer documentation.

### Added

- PostgreSQL predefined query connector
- YugabyteDB predefined query connector using YSQL/PostgreSQL-compatible protocol
- Aurora MySQL-compatible connector
- 26 supplementary predefined database queries:
  - PostgreSQL: PGX-001 to PGX-008
  - YugabyteDB: YBX-001 to YBX-008
  - Aurora MySQL: MYX-001 to MYX-010
- Frontend support for supplementary PGX/YBX/MYX controls
- Technology filter on Predefined Queries page
- Run Query button support for PostgreSQL, YugabyteDB, and Aurora MySQL controls
- Execution history support for supplementary database controls
- Database onboarding diagnostics
- Developer documentation for predefined database query setup
- Frontend regression tests for supplementary database query visibility and run enablement

### Validated

The following representative controls were successfully executed:

- PGX-001 — PostgreSQL SSL check
- YBX-001 — YugabyteDB cluster server check
- MYX-001 — Aurora MySQL/MySQL SSL capability check

Validation covered:

- Docker-based PostgreSQL
- Docker-based YugabyteDB
- Docker-based MySQL 8 as Aurora MySQL-compatible local simulator
- CLI execution
- Frontend visibility
- Frontend Run Query flow
- Execution history
- Unit/regression tests

### Developer Notes

For local Docker testing, the expected database defaults are:

PostgreSQL:

- ECS_PG_HOST=127.0.0.1
- ECS_PG_PORT=5432
- ECS_PG_DATABASE=ecs_demo
- ECS_PG_USER=ecs_user
- ECS_PG_PASSWORD=ecs_password
- ECS_PG_SSLMODE=disable

YugabyteDB:

- ECS_YB_HOST=127.0.0.1
- ECS_YB_PORT=5433
- ECS_YB_DATABASE=yugabyte
- ECS_YB_USER=yugabyte
- ECS_YB_PASSWORD=yugabyte
- ECS_YB_SSLMODE=disable

Aurora MySQL-compatible MySQL:

- ECS_MYSQL_HOST=127.0.0.1
- ECS_MYSQL_PORT=3306
- ECS_MYSQL_DATABASE=ecs_demo
- ECS_MYSQL_USER=ecs_user
- ECS_MYSQL_PASSWORD=ecs_password
- ECS_MYSQL_SSL=false

> These are local, non-production demo defaults for Docker validation only. Do not
> use these credentials outside local development; for UAT/cloud, set real
> endpoints and read-only credentials via `.env` / environment YAML. See
> [docs/DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md](docs/DEVELOPER/PREDEFINED_DATABASE_QUERY_MODULE.md).

### Tag

- ecs-predefined-db-complete-v1
