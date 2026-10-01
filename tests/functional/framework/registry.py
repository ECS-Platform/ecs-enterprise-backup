"""Use-case registry loader. The registry JSON is GENERATED from the workbook by tools/build_registry.py
(`registry/ecs_test_registry.json`); nothing here duplicates workbook metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "registry" / "ecs_test_registry.json"


@dataclass(frozen=True)
class TestDefinition:
    __test__ = False
    id: str
    uc: str
    uc_name: str
    name: str
    preconditions: str
    steps: str
    expected: str
    priority: str
    type: str
    topic: str            # cross-cutting topic ("" for use-case specific functional tests)
    automation_capability: str
    dependencies: tuple[str, ...]
    markers: tuple[str, ...]

    @property
    def is_crosscutting(self) -> bool:
        return bool(self.topic)


@lru_cache(maxsize=1)
def load_raw() -> dict[str, Any]:
    with open(REGISTRY_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def all_tests() -> dict[str, TestDefinition]:
    out: dict[str, TestDefinition] = {}
    for uc, body in load_raw()["use_cases"].items():
        for t in body["tests"]:
            out[t["id"]] = TestDefinition(uc=uc, uc_name=body["name"], dependencies=tuple(t.get("dependencies", [])),
                                          markers=tuple(t.get("markers", [])),
                                          **{k: t[k] for k in ("id", "name", "preconditions", "steps", "expected", "priority",
                                                               "type", "topic", "automation_capability")})
    return out


def tests_for(uc: str) -> list[TestDefinition]:
    return [t for t in all_tests().values() if t.uc == uc]


def get(test_id: str) -> TestDefinition:
    return all_tests()[test_id]


def use_cases() -> dict[str, str]:
    return {uc: body["name"] for uc, body in load_raw()["use_cases"].items()}
