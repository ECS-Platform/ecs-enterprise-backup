"""Aerospike connector for predefined query execution.

Aerospike checks run the read-only ``asinfo`` / ``asadm`` CLI tools **inside** the
Aerospike container (``ecs-aerospike``), so this reuses the existing docker-exec
``LinuxConnector`` rather than adding an Aerospike client dependency or
duplicating connector logic (consistent with the Redis connector).

Safety / demo behaviour:
  * Commands are curated and credential-free; host/port/namespace come from env
    (``AEROSPIKE_HOST`` / ``AEROSPIKE_PORT`` / ``AEROSPIKE_NAMESPACE``).
  * If the container / tools are unavailable, execution falls back to
    **deterministic demo output** *only in demo mode* — never a crash, never a
    live call to an unconfigured target. This mirrors ECS's offline-first pattern.
  * No secrets or IPs are stored here.

Local defaults (host port 3000 is taken by Gitea, so Aerospike uses 13000):
    AEROSPIKE_HOST=localhost  AEROSPIKE_PORT=13000  AEROSPIKE_NAMESPACE=test
"""

from __future__ import annotations

import os
from typing import Any

from modules.operations.engines.linux_connector import LinuxConnector, _timeout_from
from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30
DEFAULT_CONTAINER = "ecs-aerospike"


def get_aerospike_config() -> dict[str, Any]:
    """Aerospike target for predefined query execution (env / YAML driven).

    Execution is via ``docker exec <container> asinfo|asadm ...``. Host/port/
    namespace are carried for command templating + diagnostics. Credentials (only
    for secured clusters) are read from env and used at execution time — never
    logged, never stored in the catalog.
    """
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("aerospike")
    container = (
        cfg.get("container")
        or os.environ.get("AEROSPIKE_CONTAINER")
        or os.environ.get("ECS_AEROSPIKE_CONTAINER")
        or DEFAULT_CONTAINER
    )
    host = (
        (str(cfg.get("host")) if cfg.get("host") else None)
        or os.environ.get("AEROSPIKE_HOST")
        or os.environ.get("ECS_AEROSPIKE_HOST")
        or "localhost"
    )
    port = int(
        cfg.get("port")
        or os.environ.get("AEROSPIKE_PORT")
        or os.environ.get("ECS_AEROSPIKE_PORT")
        or 13000
    )
    namespace = (
        (str(cfg.get("namespace")) if cfg.get("namespace") else None)
        or os.environ.get("AEROSPIKE_NAMESPACE")
        or os.environ.get("ECS_AEROSPIKE_NAMESPACE")
        or "test"
    )
    password_env = str(cfg.get("password_env") or "AEROSPIKE_PASSWORD")
    return {
        "container": container,
        "host": host,
        "port": port,
        "namespace": namespace,
        "user": os.environ.get("AEROSPIKE_USER", ""),
        "password": os.environ.get(password_env) or os.environ.get("AEROSPIKE_PASSWORD", ""),
        "tls_enabled": str(os.environ.get("AEROSPIKE_TLS_ENABLED", "false")).lower() in ("1", "true", "yes"),
        "timeout_sec": _timeout_from(cfg, "AEROSPIKE_TIMEOUT_SECONDS", "ECS_AEROSPIKE_TIMEOUT_SECONDS"),
    }


def _demo_mode() -> bool:
    return str(os.environ.get("DEMO_MODE", "")).lower() in ("1", "true", "yes")


def _resolve_namespace(command: str, namespace: str) -> str:
    """Expand the ``${AEROSPIKE_NAMESPACE:-test}`` placeholder in a catalog command."""
    return command.replace("${AEROSPIKE_NAMESPACE:-test}", namespace or "test")


class AerospikeConnector(LinuxConnector):
    """Live Aerospike execution via ``asinfo``/``asadm`` inside the container.

    Subclasses :class:`LinuxConnector` (docker exec) — no duplicate execution
    logic. Namespace placeholders in the catalog command are resolved from the
    configured namespace before running.
    """

    technology = "Aerospike"

    def __init__(self, container: str = DEFAULT_CONTAINER, host: str = "localhost",
                 port: int = 13000, namespace: str = "test", user: str = "",
                 password: str = "", tls_enabled: bool = False,
                 timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        super().__init__(container=container, timeout_sec=timeout_sec)
        self.host = host
        self.port = port
        self.namespace = namespace
        self.user = user
        self.password = password
        self.tls_enabled = tls_enabled

    def execute(self, query: str) -> ConnectorResult:
        cmd = _resolve_namespace((query or "").strip(), self.namespace)
        return super().execute(cmd)


# --------------------------------------------------------------------------- #
# Deterministic demo output (used only in demo mode when tools are unavailable)
# --------------------------------------------------------------------------- #
#: Per-control canned output that is realistic but synthetic. No secrets/IPs.
_DEMO_OUTPUT: dict[str, str] = {
    "ASX-001": "build\t7.1.0.0",
    "ASX-002": "status\tok",
    "ASX-003": "namespaces\ttest",
    "ASX-004": "get-config:context=namespace;id=test\treplication-factor=2;default-ttl=0;"
               "storage-engine=memory;strong-consistency=false;nsup-period=120",
    "ASX-005": "get-config:context=security\tenable-security=false;log.report-authentication=true",
    "ASX-006": "No users found (security not enabled)",
    "ASX-007": "get-config:context=network\ttls[0].name=;service.tls-port=0;heartbeat.tls-port=0",
    "ASX-008": "get-config:context=service\tservice.port=3000;fabric.port=3001;heartbeat.port=3002;info.port=3003",
    "ASX-009": "get-config:context=namespace;id=test\tstorage-engine=memory;data-in-index=false;"
               "single-bin=false",
    "ASX-010": "~~~ Aerospike Configuration (demo) ~~~\nnamespace test: replication-factor=2",
    "ASX-011": "get-config:context=xdr\tdcs=;src-id=0;enable-xdr=false",
    "ASX-012": "get-config:context=security\tlog.report-data-op=false;log.report-sys-admin=true",
    "ASX-013": "~~~ Aerospike Statistics (demo) ~~~\nmemory_used_bytes=10485760;cluster_size=1",
    "ASX-014": "statistics\tmemory_used_sindex_bytes=0;query_reqs=0",
    "ASX-015": "statistics\tcluster_size=1;cluster_key=BB9000000000000",
    "ASX-016": "get-config:context=namespace;id=test\treplication-factor=2",
    "ASX-017": "get-config:context=namespace;id=test\tstrong-consistency=false",
    "ASX-018": "get-config:context=namespace;id=test\tdefault-ttl=0;nsup-period=120",
    "ASX-019": "sindex\t(no secondary indexes defined)",
    "ASX-020": "statistics\tclient_read_success=0;client_write_success=0;batch_sub_read_success=0",
}


def demo_output_for(control_id: str, command: str) -> str:
    """Deterministic synthetic output for a control (demo mode only)."""
    body = _DEMO_OUTPUT.get(control_id, f"{command}\t(demo output — Aerospike tools not available)")
    return f"[DEMO] {body}"
