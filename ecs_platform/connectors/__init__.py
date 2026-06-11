"""ECS connector framework: base contract, shared HTTP client, and factory."""

from ecs_platform.connectors.base import (
    BaseConnector,
    ConnectorAuthError,
    ConnectorConfig,
    ConnectorError,
    ConnectorHealth,
    EvidenceItem,
)
from ecs_platform.connectors.factory import ConnectorFactory

__all__ = [
    "BaseConnector",
    "ConnectorConfig",
    "ConnectorError",
    "ConnectorAuthError",
    "ConnectorHealth",
    "EvidenceItem",
    "ConnectorFactory",
]
