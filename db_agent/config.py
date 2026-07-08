"""DB Agent configuration (prototype).

Simple, configuration-only resolution — env vars first, then an optional YAML
file (``DB_AGENT_CONFIG`` path or ``config/db_agent.yaml``), then a safe default.
There are NO hardcoded production IPs or credentials: every default is either an
empty string or an obvious local placeholder, so a value only ever comes from
configuration.

Placeholders supported (all optional; the agent starts even if unset):
    DB_HOST DB_PORT DB_NAME DB_USERNAME DB_PASSWORD DB_SSLMODE DB_TIMEOUT_SEC
    SSH_HOST SSH_PORT SSH_USERNAME SSH_PASSWORD SSH_TIMEOUT_SEC
    DB_AGENT_HOST DB_AGENT_PORT

Security is prototype-open by default. Optional future security is gated behind
``ENABLE_*`` flags that all default to ``false`` (see :mod:`db_agent.security`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# ------------------------------------------------------------------ defaults --
# Deliberately non-production, non-secret placeholders. A real value must come
# from configuration (env/YAML); nothing here is a hardcoded bank endpoint.
_DEFAULTS: dict[str, str] = {
    "DB_HOST": "",
    "DB_PORT": "5432",
    "DB_NAME": "",
    "DB_USERNAME": "",
    "DB_PASSWORD": "",
    "DB_SSLMODE": "",
    "DB_TIMEOUT_SEC": "30",
    "SSH_HOST": "",
    "SSH_PORT": "22",
    "SSH_USERNAME": "",
    "SSH_PASSWORD": "",
    "SSH_TIMEOUT_SEC": "10",
    "DB_AGENT_HOST": "127.0.0.1",
    "DB_AGENT_PORT": "8099",
}

#: Optional security extension flags — ALL default OFF (prototype is open).
_SECURITY_FLAGS = (
    "ENABLE_MTLS",
    "ENABLE_JWT",
    "ENABLE_VAULT",
    "ENABLE_OIDC",
    "ENABLE_CERT_AUTH",
)

_TRUTHY = {"1", "true", "yes", "on"}


def _yaml_config() -> dict[str, Any]:
    """Load the optional YAML config (never raises; returns {} on any problem)."""
    path = os.environ.get("DB_AGENT_CONFIG", "").strip() or "config/db_agent.yaml"
    try:
        import yaml  # PyYAML is already an ECS dependency

        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 - config is optional; never block startup
        return {}


def _clean(value: Any) -> str:
    """String-coerce, treating unresolved ``${...}`` placeholders as empty."""
    s = str(value).strip() if value is not None else ""
    return "" if s.startswith("${") else s


# Map each env-key prefix to the YAML section(s) it may live under, and the
# short field name within that section. This prevents cross-section bleed (e.g.
# SSH_HOST must never resolve from db.host).
_KEY_TO_SECTION: dict[str, tuple[tuple[str, ...], str]] = {
    "DB_HOST": (("db", "database"), "host"),
    "DB_PORT": (("db", "database"), "port"),
    "DB_NAME": (("db", "database"), "name"),
    "DB_USERNAME": (("db", "database"), "username"),
    "DB_PASSWORD": (("db", "database"), "password"),
    "DB_SSLMODE": (("db", "database"), "sslmode"),
    "DB_TIMEOUT_SEC": (("db", "database"), "timeout_sec"),
    "SSH_HOST": (("ssh", "server"), "host"),
    "SSH_PORT": (("ssh", "server"), "port"),
    "SSH_USERNAME": (("ssh", "server"), "username"),
    "SSH_PASSWORD": (("ssh", "server"), "password"),
    "SSH_TIMEOUT_SEC": (("ssh", "server"), "timeout_sec"),
    "DB_AGENT_HOST": (("agent",), "host"),
    "DB_AGENT_PORT": (("agent",), "port"),
}


def _resolve(key: str, yaml_cfg: dict[str, Any]) -> str:
    """Resolve one key: env var > yaml section field > flat yaml key > default.

    YAML lookups are scoped to the key's OWN section (via ``_KEY_TO_SECTION``) so
    a DB field can never leak into an SSH field or vice versa.
    """
    env_val = _clean(os.environ.get(key))
    if env_val:
        return env_val
    sections, short = _KEY_TO_SECTION.get(key, ((), key.lower()))
    for section in sections:
        block = yaml_cfg.get(section)
        if isinstance(block, dict):
            v = _clean(block.get(short))
            if v:
                return v
    # Flat (un-sectioned) YAML key fallback, e.g. DB_HOST: ... at the top level.
    flat = _clean(yaml_cfg.get(key) or yaml_cfg.get(key.lower()))
    if flat:
        return flat
    return _DEFAULTS.get(key, "")


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


@dataclass
class DbTarget:
    host: str = ""
    port: int = 5432
    name: str = ""
    username: str = ""
    password: str = ""
    sslmode: str = ""
    timeout_sec: int = 30

    @property
    def configured(self) -> bool:
        return bool(self.host and self.name and self.username)


@dataclass
class SshTarget:
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    timeout_sec: int = 10

    @property
    def configured(self) -> bool:
        return bool(self.host and self.username)


@dataclass
class AgentConfig:
    host: str = "127.0.0.1"
    port: int = 8099
    db: DbTarget = field(default_factory=DbTarget)
    ssh: SshTarget = field(default_factory=SshTarget)
    security: dict[str, bool] = field(default_factory=dict)

    def masked(self) -> dict[str, Any]:
        """Secret-free snapshot for logs / the /config endpoint (never a secret)."""
        def m(v: str) -> str:
            return "SET" if v else "MISSING"
        return {
            "prototype": True,
            "production_secure": False,
            "agent": {"host": self.host, "port": self.port},
            "db": {
                "host": self.db.host or "(unset)",
                "port": self.db.port,
                "name": self.db.name or "(unset)",
                "username": m(self.db.username),
                "password": m(self.db.password),
                "sslmode": self.db.sslmode or "(default)",
                "timeout_sec": self.db.timeout_sec,
                "configured": self.db.configured,
            },
            "ssh": {
                "host": self.ssh.host or "(unset)",
                "port": self.ssh.port,
                "username": m(self.ssh.username),
                "password": m(self.ssh.password),
                "timeout_sec": self.ssh.timeout_sec,
                "configured": self.ssh.configured,
            },
            "security": self.security,
        }


def load_config() -> AgentConfig:
    """Resolve the full agent configuration. Never raises.

    Security flags all default OFF, so a missing security stack never blocks the
    agent. DB/SSH targets are optional — an unconfigured target simply reports
    ``configured=false`` and connectivity checks degrade gracefully.
    """
    y = _yaml_config()
    db = DbTarget(
        host=_resolve("DB_HOST", y),
        port=_safe_int(_resolve("DB_PORT", y), 5432),
        name=_resolve("DB_NAME", y),
        username=_resolve("DB_USERNAME", y),
        password=_resolve("DB_PASSWORD", y),
        sslmode=_resolve("DB_SSLMODE", y),
        timeout_sec=_safe_int(_resolve("DB_TIMEOUT_SEC", y), 30),
    )
    ssh = SshTarget(
        host=_resolve("SSH_HOST", y),
        port=_safe_int(_resolve("SSH_PORT", y), 22),
        username=_resolve("SSH_USERNAME", y),
        password=_resolve("SSH_PASSWORD", y),
        timeout_sec=_safe_int(_resolve("SSH_TIMEOUT_SEC", y), 10),
    )
    security = {flag: _clean(os.environ.get(flag)).lower() in _TRUTHY for flag in _SECURITY_FLAGS}
    return AgentConfig(
        host=_resolve("DB_AGENT_HOST", y) or "127.0.0.1",
        port=_safe_int(_resolve("DB_AGENT_PORT", y), 8099),
        db=db,
        ssh=ssh,
        security=security,
    )
