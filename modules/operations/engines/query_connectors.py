"""Connector interfaces for predefined query execution (interfaces only — no runtime implementation)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Predefined-query execution targets are now sourced from the active ECS
# environment (config/environments/<ECS_ENV>.yaml) via config.environment_loader.
# The static map below is a SAFE FALLBACK only — used verbatim when the
# environment layer is unavailable, so historical demo behaviour is preserved.
# ---------------------------------------------------------------------------
_STATIC_CONNECTOR_CONFIG: dict[str, dict[str, str | int]] = {
    "postgres-demo": {"type": "PostgreSQLConnector", "technology": "PostgreSQL", "host": "postgres-demo", "port": 5432},
    "ubuntu-demo": {"type": "LinuxConnector", "technology": "Linux", "host": "ubuntu-demo", "port": 0},
    "sonarqube-demo": {"type": "SonarQubeConnector", "technology": "SonarQube", "host": "sonarqube-demo", "port": 9000},
    "trivy": {"type": "TrivyConnector", "technology": "Trivy", "host": "aquasec/trivy", "port": 0},
    "gitleaks": {"type": "GitLeaksConnector", "technology": "GitLeaks", "host": "zricethezav/gitleaks", "port": 0},
    "postgres-db": {"type": "DatabaseConnector", "technology": "PostgreSQL", "host": "postgres-db", "port": 5432},
    "oracle-db": {"type": "DatabaseConnector", "technology": "Oracle", "host": "oracle-db", "port": 1521},
    "ubuntu-host": {"type": "SSHConnector", "technology": "Linux", "host": "ubuntu-host", "port": 22},
    "sonarqube-server": {"type": "APIConnector", "technology": "SonarQube", "host": "sonarqube-server", "port": 9000},
}


def _env_predefined_targets() -> dict[str, Any]:
    """Predefined-query targets from the active environment config (never raises)."""
    try:
        from config.environment_loader import get_predefined_query_targets

        return get_predefined_query_targets() or {}
    except Exception:  # noqa: BLE001 - degrade to static fallback, never break callers
        return {}


def get_predefined_target(name: str) -> dict[str, Any]:
    """Return one predefined-query target block (e.g. 'postgresql') as a dict."""
    block = _env_predefined_targets().get(name)
    return dict(block) if isinstance(block, dict) else {}


def build_connector_config() -> dict[str, dict[str, str | int]]:
    """Build the connector target map from the active environment.

    Combines the live demo connectors with the per-environment OS/DB/middleware
    server lists. Falls back to the static map when the environment layer yields
    nothing, so the result is never empty.
    """
    targets = _env_predefined_targets()
    if not targets:
        return dict(_STATIC_CONNECTOR_CONFIG)

    cfg: dict[str, dict[str, str | int]] = {}
    pg = targets.get("postgresql") or {}
    cfg["postgres-demo"] = {"type": "PostgreSQLConnector", "technology": "PostgreSQL",
                            "host": str(pg.get("host") or "postgres-demo"), "port": int(pg.get("port") or 5432)}
    lx = targets.get("linux") or {}
    cfg["ubuntu-demo"] = {"type": "LinuxConnector", "technology": "Linux",
                          "host": str(lx.get("container") or "ubuntu-demo"), "port": 0}
    sq = targets.get("sonarqube") or {}
    cfg["sonarqube-demo"] = {"type": "SonarQubeConnector", "technology": "SonarQube",
                             "host": str(sq.get("base_url") or "sonarqube-demo"), "port": 9000}

    for host in targets.get("os_servers") or []:
        cfg[str(host)] = {"type": "SSHConnector", "technology": "Linux", "host": str(host), "port": 22}
    for host in targets.get("db_servers") or []:
        cfg[str(host)] = {"type": "DatabaseConnector", "technology": "PostgreSQL", "host": str(host), "port": 5432}
    for host in targets.get("middleware_servers") or []:
        cfg[str(host)] = {"type": "APIConnector", "technology": "Middleware", "host": str(host), "port": 443}

    # Ensure the map is never smaller than the static baseline for legacy checks.
    for key, val in _STATIC_CONNECTOR_CONFIG.items():
        cfg.setdefault(key, val)
    return cfg


#: Backwards-compatible module-level map (env-derived, static fallback).
CONNECTOR_CONFIG: dict[str, dict[str, str | int]] = build_connector_config()


@dataclass
class ConnectorResult:
    success: bool
    output: str = ""
    error_message: str = ""
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """Shared connector contract for predefined query execution."""

    technology: str = ""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the target environment."""

    @abstractmethod
    def execute(self, query: str) -> ConnectorResult:
        """Execute a predefined query and return structured output."""

    @abstractmethod
    def disconnect(self) -> None:
        """Release connection resources."""


class DatabaseConnector(BaseConnector):
    """Database targets: PostgreSQL, Oracle, and similar SQL engines."""

    def __init__(self, host: str = "", port: int = 0, database: str = "", user: str = "", password: str = "", technology: str = ""):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.technology = technology
        self._connected = False

    def connect(self) -> bool:
        raise NotImplementedError("DatabaseConnector.connect() — execution not yet enabled")

    def execute(self, query: str) -> ConnectorResult:
        raise NotImplementedError("DatabaseConnector.execute() — execution not yet enabled")

    def disconnect(self) -> None:
        self._connected = False


class SSHConnector(BaseConnector):
    """SSH targets: Linux and Windows command execution via remote shell."""

    def __init__(self, host: str = "", port: int = 22, user: str = "", key_path: str = "", technology: str = "Linux"):
        self.host = host
        self.port = port
        self.user = user
        self.key_path = key_path
        self.technology = technology
        self._connected = False

    def connect(self) -> bool:
        raise NotImplementedError("SSHConnector.connect() — execution not yet enabled")

    def execute(self, query: str) -> ConnectorResult:
        raise NotImplementedError("SSHConnector.execute() — execution not yet enabled")

    def disconnect(self) -> None:
        self._connected = False


class APIConnector(BaseConnector):
    """API targets: SonarQube, GitLeaks orchestration endpoints, and similar HTTP services."""

    def __init__(self, base_url: str = "", token: str = "", technology: str = ""):
        self.base_url = base_url
        self.token = token
        self.technology = technology
        self._connected = False

    def connect(self) -> bool:
        raise NotImplementedError("APIConnector.connect() — execution not yet enabled")

    def execute(self, query: str) -> ConnectorResult:
        raise NotImplementedError("APIConnector.execute() — execution not yet enabled")

    def disconnect(self) -> None:
        self._connected = False


def connector_for_technology(technology: str) -> BaseConnector | None:
    """Map derived technology to the appropriate connector interface."""
    if not technology or technology == "Unknown":
        return None
    if technology == "PostgreSQL":
        try:
            from modules.operations.engines.postgresql_connector import PostgreSQLConnector, get_postgresql_config
        except ImportError:
            # psycopg2 (or another driver dependency) is not installed in this
            # environment. Degrade gracefully so callers can surface a friendly
            # message instead of a 500 / raw ModuleNotFoundError.
            return None
        return PostgreSQLConnector(**get_postgresql_config())
    if technology == "YugabyteDB":
        try:
            from modules.operations.engines.yugabyte_connector import YugabyteConnector, get_yugabyte_config
        except ImportError:
            return None
        return YugabyteConnector(**get_yugabyte_config())
    if technology == "Aurora MySQL":
        try:
            from modules.operations.engines.mysql_connector import MySQLConnector, get_mysql_config
        except ImportError:
            # PyMySQL not installed — degrade gracefully.
            return None
        return MySQLConnector(**get_mysql_config())
    if technology == "SQL Server":
        try:
            from modules.operations.engines.sqlserver_connector import SQLServerConnector, get_sqlserver_config
        except ImportError:
            return None
        return SQLServerConnector(**get_sqlserver_config())
    if technology == "MongoDB":
        try:
            from modules.operations.engines.mongodb_connector import MongoDBConnector, get_mongodb_config
        except ImportError:
            return None
        return MongoDBConnector(**get_mongodb_config())
    if technology == "Redis":
        try:
            from modules.operations.engines.redis_connector import RedisConnector, get_redis_config
        except ImportError:
            return None
        return RedisConnector(**get_redis_config())
    if technology == "Aerospike":
        # Aerospike runs read-only asinfo/asadm via docker exec (LinuxConnector
        # subclass) — no extra client dependency, consistent with Redis.
        from modules.operations.engines.aerospike_connector import (
            AerospikeConnector, get_aerospike_config,
        )

        return AerospikeConnector(**get_aerospike_config())
    if technology == "Apache HTTPD":
        from modules.operations.engines.linux_connector import LinuxConnector, get_apache_config

        return LinuxConnector(**get_apache_config())
    if technology == "Tomcat":
        from modules.operations.engines.linux_connector import LinuxConnector, get_tomcat_config

        return LinuxConnector(**get_tomcat_config())
    if technology == "Kubernetes":
        from modules.operations.engines.kubernetes_connector import KubernetesConnector, get_kubernetes_config

        return KubernetesConnector(**get_kubernetes_config())
    if technology == "OpenShift":
        from modules.operations.engines.kubernetes_connector import OpenShiftConnector, get_openshift_config

        return OpenShiftConnector(**get_openshift_config())
    if technology == "Oracle":
        try:
            from modules.operations.engines.oracle_connector import OracleConnector, get_oracle_config
        except ImportError:
            return None
        return OracleConnector(**get_oracle_config())
    if technology == "NGINX":
        from modules.operations.engines.linux_connector import LinuxConnector, get_nginx_config

        return LinuxConnector(**get_nginx_config())
    if technology == "Red Hat Enterprise Linux 8.x":
        from modules.operations.engines.linux_connector import LinuxConnector, get_rhel_config

        return LinuxConnector(**get_rhel_config(8))
    if technology == "Red Hat Enterprise Linux 9.x":
        from modules.operations.engines.linux_connector import LinuxConnector, get_rhel_config

        return LinuxConnector(**get_rhel_config(9))
    if technology == "Linux":
        from modules.operations.engines.linux_connector import LinuxConnector, get_linux_config

        return LinuxConnector(**get_linux_config())
    if technology == "SonarQube":
        from modules.operations.engines.sonarqube_connector import SonarQubeConnector, get_sonarqube_config

        return SonarQubeConnector(**get_sonarqube_config())
    if technology == "Trivy":
        from modules.operations.engines.trivy_connector import TrivyConnector, get_trivy_config

        return TrivyConnector(**get_trivy_config())
    if technology == "GitLeaks":
        from modules.operations.engines.gitleaks_connector import GitLeaksConnector, get_gitleaks_config

        return GitLeaksConnector(**get_gitleaks_config())
    if technology == "Windows":
        return SSHConnector(technology=technology)
    return None
