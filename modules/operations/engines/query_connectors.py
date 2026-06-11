"""Connector interfaces for predefined query execution (interfaces only — no runtime implementation)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Prepared connector targets for future Docker demo environment integration.
CONNECTOR_CONFIG: dict[str, dict[str, str | int]] = {
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
    if technology == "Oracle":
        return DatabaseConnector(technology=technology)
    if technology in ("Windows", "NGINX"):
        return SSHConnector(technology=technology)
    return None
