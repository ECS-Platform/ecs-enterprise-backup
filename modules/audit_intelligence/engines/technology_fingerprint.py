"""Technology fingerprinting engine (Milestone 1, Module 2).

Deterministically infers an asset's technology (and, where possible, a version)
from discovery signals — container image, service/host name, listening ports,
CMDB class, etc. — and assigns a confidence score in ``[0.0, 1.0]``.

Design:
  * Deterministic and offline — pure functions over the provided hints.
  * Technology names align with the predefined-query catalog so fingerprints link
    cleanly to controls/frameworks (Module 1). ``matched_catalog_technology`` flags
    whether the inferred technology actually exists in the catalog.
  * Rule-based and explainable — every inference records the ``signals`` that drove
    it, so results are auditable.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from modules.audit_intelligence.models import TechnologyFingerprint

# Confidence weights per signal source (highest wins; small boosts stack).
_CONF_IMAGE = 0.9          # explicit container image is very reliable
_CONF_EXPLICIT = 0.95      # caller stated the technology directly
_CONF_NAME = 0.6           # host/service/container name hint
_CONF_PORT = 0.5           # listening port hint
_CONF_CLASS = 0.55         # CMDB class / asset type hint
_CONF_BOOST = 0.05         # corroborating secondary signal

#: Ordered (regex, canonical technology) rules matched against image/name text.
#: Order matters: more specific patterns first (e.g. yugabyte before generic pg).
_TEXT_RULES: list[tuple[str, str]] = [
    (r"yugabyte|yugabytedb|\bysql\b", "YugabyteDB"),
    (r"aurora|mariadb|percona|mysql", "Aurora MySQL"),
    (r"postgres|postgresql|pgvector|pgbouncer", "PostgreSQL"),
    (r"oracle|oracledb|ords|orcl", "Oracle"),
    (r"sqlserver|mssql|sql-server|azure-sql", "SQL Server"),
    (r"mongo|mongodb", "MongoDB"),
    (r"aerospike|asinfo|asadm", "Aerospike"),
    (r"redis|valkey", "Redis"),
    (r"nginx", "NGINX"),
    (r"httpd|apache2|apache-httpd|\bapache\b", "Apache HTTPD"),
    (r"tomcat|catalina", "Tomcat"),
    (r"openshift|\bocp\b|\boc\b", "OpenShift"),
    (r"kubernetes|k8s|kubectl|kube-", "Kubernetes"),
    (r"rhel.?9|redhat.?9|rhel9|ubi9", "Red Hat Enterprise Linux 9.x"),
    (r"rhel.?8|redhat.?8|rhel8|ubi8", "Red Hat Enterprise Linux 8.x"),
    (r"windows|win-?server|mswin", "Windows"),
    (r"ubuntu|debian|alpine|centos|linux", "Linux"),
]

#: Well-known default ports -> canonical technology.
_PORT_RULES: dict[int, str] = {
    5432: "PostgreSQL",
    5433: "YugabyteDB",
    3306: "Aurora MySQL",
    1521: "Oracle",
    1433: "SQL Server",
    27017: "MongoDB",
    6379: "Redis",
    3000: "Aerospike",    # Aerospike client service port (host-mapped to 13000 locally)
    13000: "Aerospike",   # ECS local host mapping (host 3000 is taken by Gitea)
    8080: "Tomcat",
    8443: "Tomcat",
    6443: "Kubernetes",
}

#: CMDB class / asset-type hints -> canonical technology (coarse).
_CLASS_RULES: list[tuple[str, str]] = [
    (r"database|db|rdbms", ""),  # class says "database" but not which -> no tech, low value
    (r"load.?balancer", "NGINX"),
    (r"kubernetes|container.?cluster|k8s", "Kubernetes"),
    (r"openshift", "OpenShift"),
]

#: A dotted version (e.g. 16.2, 9.4.1). Bare single integers are intentionally
#: NOT treated as versions to avoid false hits from names like "ecs-redis-1".
_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")
#: An image tag that is a bare major version (e.g. "mongo:7", "tomcat:9").
_IMAGE_MAJOR_RE = re.compile(r"^\d+$")


@lru_cache(maxsize=1)
def _catalog_technologies_lower() -> frozenset[str]:
    """Lower-cased set of technology names present in the query catalog."""
    from modules.audit_intelligence.engines import technology_control_mapping as mapping

    return frozenset(t.lower() for t in mapping.technology_names())


def reset_cache() -> None:
    _catalog_technologies_lower.cache_clear()


def _match_text(text: str) -> str | None:
    if not text:
        return None
    low = text.lower()
    for pattern, tech in _TEXT_RULES:
        if re.search(pattern, low):
            return tech
    return None


def _match_ports(ports: Any) -> str | None:
    for p in _iter_ports(ports):
        tech = _PORT_RULES.get(p)
        if tech:
            return tech
    return None


def _iter_ports(ports: Any) -> list[int]:
    """Extract integer container ports from compose-style port specs or a list."""
    result: list[int] = []
    if not ports:
        return result
    if isinstance(ports, (str, int)):
        ports = [ports]
    for item in ports:
        # compose forms: 5432, "5432", "15432:5432", "127.0.0.1:15432:5432/tcp"
        text = str(item).split("/")[0]
        parts = text.split(":")
        candidate = parts[-1] if parts else text
        try:
            result.append(int(candidate))
        except (TypeError, ValueError):
            continue
    return result


def _extract_version_from_image(image: str) -> str:
    """Version from an image tag only (e.g. ``postgres:16.2`` -> 16.2, ``mongo:7`` -> 7).

    Only the tag portion after the last ':' is considered, and a bare integer tag
    is accepted as a major version. Names/banners are NOT parsed here to avoid
    false positives from index suffixes (e.g. ``ecs-redis-1``).
    """
    if not image or ":" not in image:
        return ""
    tag = image.rsplit(":", 1)[-1].strip()
    m = _VERSION_RE.search(tag)
    if m:
        return m.group(1)
    if _IMAGE_MAJOR_RE.match(tag):
        return tag
    return ""


def fingerprint_asset(hints: dict[str, Any]) -> TechnologyFingerprint:
    """Infer technology/version/confidence from discovery signals.

    Recognized hint keys (all optional): ``technology`` (explicit), ``image``,
    ``name``, ``service``, ``container_name``, ``asset_class``, ``asset_type``,
    ``ports``, ``version``, ``operating_system``.
    """
    hints = hints or {}
    signals: list[str] = []
    technology = ""
    confidence = 0.0
    primary = ""  # which signal source determined the technology

    explicit = str(hints.get("technology") or "").strip()
    image = str(hints.get("image") or "").strip()
    name_text = " ".join(
        str(hints.get(k) or "")
        for k in ("name", "service", "container_name")
    ).strip()
    class_text = " ".join(
        str(hints.get(k) or "") for k in ("asset_class", "asset_type")
    ).strip()
    ports = hints.get("ports")

    # 1. Explicit technology (highest confidence).
    if explicit:
        technology = _canonicalize(explicit)
        confidence = _CONF_EXPLICIT
        primary = "explicit"
        signals.append(f"explicit technology: {explicit}")

    # 2. Container image (very reliable).
    if not technology:
        tech = _match_text(image)
        if tech:
            technology, confidence, primary = tech, _CONF_IMAGE, "image"
            signals.append(f"image: {image}")

    # 3. Host / service / container name.
    if not technology:
        tech = _match_text(name_text)
        if tech:
            technology, confidence, primary = tech, _CONF_NAME, "name"
            signals.append(f"name: {name_text}")

    # 4. Listening port.
    if not technology:
        tech = _match_ports(ports)
        if tech:
            technology, confidence, primary = tech, _CONF_PORT, "port"
            signals.append(f"port match: {_iter_ports(ports)}")

    # 5. CMDB class / asset type (coarse).
    if not technology and class_text:
        low = class_text.lower()
        for pattern, tech in _CLASS_RULES:
            if tech and re.search(pattern, low):
                technology, confidence, primary = tech, _CONF_CLASS, "class"
                signals.append(f"class: {class_text}")
                break

    # Corroborating secondary signals (small confidence boosts).
    if technology:
        confidence = _boost(
            confidence, technology, primary, image, name_text, ports, signals
        )

    if not technology:
        # No signal matched -> Unknown, but note anything we did see.
        note = image or name_text or class_text
        if note:
            signals.append(f"no rule matched: {note}")
        return TechnologyFingerprint(
            technology="Unknown",
            confidence=0.0,
            version="",
            signals=tuple(signals),
            matched_catalog_technology=False,
        )

    version = str(hints.get("version") or "").strip() or _extract_version_from_image(image)
    matched = technology.lower() in _catalog_technologies_lower()
    return TechnologyFingerprint(
        technology=technology,
        confidence=min(confidence, 1.0),
        version=version,
        signals=tuple(signals),
        matched_catalog_technology=matched,
    )


def _boost(
    confidence: float,
    technology: str,
    primary: str,
    image: str,
    name_text: str,
    ports: Any,
    signals: list[str],
) -> float:
    """Add a small boost for each independent secondary signal that agrees.

    ``primary`` is the signal source that already determined ``technology``; it is
    excluded so we only credit *corroborating* evidence.
    """
    boosts = 0
    if primary != "image" and image and _match_text(image) == technology:
        boosts += 1
        signals.append("corroborated by image")
    if primary != "name" and name_text and _match_text(name_text) == technology:
        boosts += 1
        signals.append("corroborated by name")
    if primary != "port" and _match_ports(ports) == technology:
        boosts += 1
        signals.append("corroborated by port")
    return confidence + boosts * _CONF_BOOST


def _canonicalize(technology: str) -> str:
    """Map a free-text technology to a catalog name where possible."""
    mapped = _match_text(technology)
    if mapped:
        return mapped
    # Keep the caller's label if it already matches a catalog technology exactly.
    if technology.lower() in _catalog_technologies_lower():
        # Return the catalog's canonical casing.
        from modules.audit_intelligence.engines import technology_control_mapping as mapping

        for name in mapping.technology_names():
            if name.lower() == technology.lower():
                return name
    return technology
