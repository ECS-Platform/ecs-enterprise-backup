"""Connector interfaces for predefined query execution (interfaces only — no runtime implementation)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Prepared connector targets for future Docker demo environment integration.
CONNECTOR_CONFIG: dict[str, dict[str, str | int]] = {
    "postgres-demo": {"type": "PostgreSQLConnector", "technology": "PostgreSQL", "host": "postgres-demo", "port": 5432},
    "postgres-db": {"type": "DatabaseConnector", "technology": "PostgreSQL", "host": "postgres-db", "port": 5432},
    "oracle-db": {"type": "DatabaseConnector", "technology": "Oracle", "host": "oracle-db", "port": 1521},
    "ubuntu-host": {"type": "SSHConnector", "technology": "Linux", "host": "ubuntu-host", "port": 22},
    "sonarqube-server": {"type": "APIConnector", "technology": "SonarQube", "host": "sonarqube-server", "port": 9000},
}


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
        from modules.operations.engines.postgresql_connector import PostgreSQLConnector, get_postgresql_config

        return PostgreSQLConnector(**get_postgresql_config())
    if technology == "Oracle":
        return DatabaseConnector(technology=technology)
    if technology in ("Linux", "Windows", "NGINX", "GitLeaks", "Trivy"):
        return SSHConnector(technology=technology)
    if technology == "SonarQube":
        return APIConnector(technology=technology)
    return None
