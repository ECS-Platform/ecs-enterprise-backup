"""Tests for the technology fingerprinting engine (M1, Module 2).

Deterministic, offline, rule-based inference from discovery signals. No live
Docker / network required.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import technology_fingerprint as fp
from modules.audit_intelligence.models import TechnologyFingerprint


@pytest.fixture(autouse=True)
def _fresh_cache():
    fp.reset_cache()
    yield
    fp.reset_cache()


# --------------------------------------------------------------------------- #
# Image-based inference
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "image,expected",
    [
        ("postgres:16.2", "PostgreSQL"),
        ("mongo:7", "MongoDB"),
        ("redis:7.2", "Redis"),
        ("nginx:1.25", "NGINX"),
        ("httpd:2.4", "Apache HTTPD"),
        ("tomcat:9", "Tomcat"),
        ("mysql:8", "Aurora MySQL"),
        ("yugabytedb/yugabyte:2.20", "YugabyteDB"),
    ],
)
def test_fingerprint_from_image(image, expected):
    f = fp.fingerprint_asset({"image": image})
    assert isinstance(f, TechnologyFingerprint)
    assert f.technology == expected
    assert f.confidence >= 0.9
    assert f.matched_catalog_technology is True


def test_version_extracted_from_image_tag():
    assert fp.fingerprint_asset({"image": "postgres:16.2"}).version == "16.2"
    assert fp.fingerprint_asset({"image": "mongo:7"}).version == "7"


def test_no_false_version_from_name_index():
    """A compose index suffix like ecs-redis-1 must NOT become a version."""
    f = fp.fingerprint_asset({"name": "ecs-redis-1", "ports": ["16379:6379"]})
    assert f.technology == "Redis"
    assert f.version == ""


# --------------------------------------------------------------------------- #
# Name / port / explicit inference
# --------------------------------------------------------------------------- #
def test_fingerprint_from_name():
    f = fp.fingerprint_asset({"name": "nginx-demo"})
    assert f.technology == "NGINX"
    assert 0.5 <= f.confidence < 0.9


def test_fingerprint_from_port_only():
    f = fp.fingerprint_asset({"name": "mystery-host", "ports": [1433]})
    assert f.technology == "SQL Server"
    assert f.confidence >= 0.5


def test_explicit_technology_highest_confidence():
    f = fp.fingerprint_asset({"technology": "Oracle"})
    assert f.technology == "Oracle"
    assert f.confidence >= 0.95


def test_image_and_port_corroborate_boost():
    only_image = fp.fingerprint_asset({"image": "mongo:7"})
    corroborated = fp.fingerprint_asset({"image": "mongo:7", "ports": [27017]})
    assert corroborated.confidence >= only_image.confidence


def test_yugabyte_before_postgres_precedence():
    # 'yugabyte' contains no 'postgres' text, but ensure the ordered rules pick YB.
    f = fp.fingerprint_asset({"image": "yugabytedb/yugabyte:2.20"})
    assert f.technology == "YugabyteDB"


def test_port_specs_parsed_various_forms():
    for spec in (["5432"], ["15432:5432"], ["127.0.0.1:15432:5432/tcp"], [5432]):
        f = fp.fingerprint_asset({"name": "x", "ports": spec})
        assert f.technology == "PostgreSQL", spec


# --------------------------------------------------------------------------- #
# Unknown handling
# --------------------------------------------------------------------------- #
def test_unknown_when_no_signal():
    f = fp.fingerprint_asset({"name": "totally-unknown-xyz"})
    assert f.technology == "Unknown"
    assert f.confidence == 0.0
    assert f.matched_catalog_technology is False


def test_empty_hints_is_unknown():
    f = fp.fingerprint_asset({})
    assert f.technology == "Unknown"
    assert f.confidence == 0.0


def test_signals_are_recorded_for_audit():
    f = fp.fingerprint_asset({"image": "postgres:16.2"})
    assert f.signals and any("image" in s for s in f.signals)


def test_to_dict_is_serializable():
    d = fp.fingerprint_asset({"image": "redis:7"}).to_dict()
    assert d["technology"] == "Redis"
    assert isinstance(d["signals"], list)
    assert isinstance(d["confidence"], float)
