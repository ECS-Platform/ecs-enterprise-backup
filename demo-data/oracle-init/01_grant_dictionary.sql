-- ECS oracle-demo one-time init (gvenzl/oracle-free convention:
-- /container-entrypoint-initdb.d/*.sql runs once, as SYSTEM, connected to the
-- FREEPDB1 pluggable database on first container init).
--
-- The ECS predefined-query Oracle connector authenticates as APP_USER (ecs_user).
-- gvenzl grants APP_USER only CONNECT/RESOURCE-style privileges, so every ORX-*
-- baseline query against V$ / DBA_ data-dictionary views fails with ORA-00942.
-- SELECT ANY DICTIONARY gives read-only visibility of those views without any
-- write or DDL capability.
GRANT SELECT ANY DICTIONARY TO ecs_user;
EXIT;
