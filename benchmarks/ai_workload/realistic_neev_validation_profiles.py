"""Realistic ECS workload scenarios for the Neev validation benchmark.

Each scenario reflects a real ECS production usage pattern (single-app, full,
multi-app, enterprise retrieval, large-repository sensitivity). Scenarios drive the
``realistic_prompt_factory`` to build a realistic ECS assessment prompt whose token
shape is MEASURED (full run) or ESTIMATED (dry run).

The scenarios are NOT tuned to reproduce the current 125K / 50K planning assumption.
Concrete values are chosen within the requested ranges to be representative; repository
size is metadata that scales retrieval realism, never an automatic evidence dump.

Pure standard library — importable on an 8 GB workstation without ECS dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from benchmarks.ai_workload.realistic_prompt_factory import PromptSpec


@dataclass
class NeevScenario:
    """One realistic ECS assessment scenario. ``group`` enables ``--profiles`` aliases."""

    key: str
    name: str
    group: str
    repository_apps: int
    apps_selected: int
    frameworks: int
    controls_per_framework: int
    evidence_files_per_framework: int
    pages_per_file: int
    words_per_page: int
    output_style: str
    output_mode: str
    evidence_excerpt_words: int = 90

    def to_prompt_spec(self) -> PromptSpec:
        # Auxiliary context volumes scale realistically with the assessment breadth.
        fw = self.frameworks
        apps = max(1, self.apps_selected)
        return PromptSpec(
            repository_apps=self.repository_apps,
            apps_selected=self.apps_selected,
            frameworks=self.frameworks,
            controls_per_framework=self.controls_per_framework,
            evidence_files_per_framework=self.evidence_files_per_framework,
            pages_per_file=self.pages_per_file,
            words_per_page=self.words_per_page,
            output_style=self.output_style,
            output_mode=self.output_mode,
            evidence_excerpt_words=self.evidence_excerpt_words,
            observation_count=max(3, fw * 2),
            vapt_count=max(3, apps * 3),
            baseline_count=max(2, apps * 2),
            exception_count=max(3, fw * 1),
            audit_comment_count=max(3, fw),
            remediation_count=max(3, fw * 1),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Concrete, representative values chosen WITHIN the requested ranges. These are the
# realistic mid/representative points (e.g. controls 20-50 -> 35-40; evidence 10-20 -> 15).
def default_profiles() -> list[NeevScenario]:
    return [
        # A. Single App Small Assessment
        NeevScenario(
            key="small", name="Single App Small Assessment", group="small",
            repository_apps=1, apps_selected=1, frameworks=3,
            controls_per_framework=20, evidence_files_per_framework=2,
            pages_per_file=2, words_per_page=500,
            output_style="short readiness summary", output_mode="summarized",
        ),
        # B. Single App Full Assessment
        NeevScenario(
            key="full", name="Single App Full Assessment", group="full",
            repository_apps=1, apps_selected=1, frameworks=10,
            controls_per_framework=35, evidence_files_per_framework=4,
            pages_per_file=2, words_per_page=500,
            output_style="framework-wise readiness report", output_mode="framework_report",
        ),
        # C. Multi App Assessment
        NeevScenario(
            key="multi_app", name="Multi App Assessment", group="multi_app",
            repository_apps=4, apps_selected=3, frameworks=10,
            controls_per_framework=40, evidence_files_per_framework=8,
            pages_per_file=2, words_per_page=500,
            output_style="consolidated audit readiness report", output_mode="consolidated",
        ),
        # D. Enterprise Retrieval Validation (200-app repository)
        NeevScenario(
            key="enterprise", name="Enterprise Retrieval Validation", group="enterprise",
            repository_apps=200, apps_selected=3, frameworks=10,
            controls_per_framework=40, evidence_files_per_framework=15,
            pages_per_file=2, words_per_page=500,
            output_style="summarized enterprise readiness assessment", output_mode="summarized",
        ),
        # E. Large Repository Sensitivity (300 / 500 / 600-app repositories)
        NeevScenario(
            key="large_repository_300", name="Large Repository Sensitivity (300 apps)",
            group="large_repository",
            repository_apps=300, apps_selected=3, frameworks=10,
            controls_per_framework=40, evidence_files_per_framework=15,
            pages_per_file=2, words_per_page=500,
            output_style="generalized summary", output_mode="summarized",
        ),
        NeevScenario(
            key="large_repository_500", name="Large Repository Sensitivity (500 apps)",
            group="large_repository",
            repository_apps=500, apps_selected=4, frameworks=10,
            controls_per_framework=40, evidence_files_per_framework=18,
            pages_per_file=2, words_per_page=500,
            output_style="generalized summary", output_mode="summarized",
        ),
        NeevScenario(
            key="large_repository_600", name="Large Repository Sensitivity (600 apps)",
            group="large_repository",
            repository_apps=600, apps_selected=4, frameworks=10,
            controls_per_framework=40, evidence_files_per_framework=20,
            pages_per_file=2, words_per_page=500,
            output_style="generalized summary", output_mode="summarized",
        ),
    ]


# ``--profiles`` accepts scenario keys, group aliases, or "all".
_GROUP_ALIASES = {"small", "full", "multi_app", "enterprise", "large_repository"}


def select_profiles(names: list[str] | None) -> list[NeevScenario]:
    """Resolve a selection of scenario keys / group aliases / "all" to scenarios.

    Unknown tokens raise a clear error listing valid keys and group aliases."""
    catalog = default_profiles()
    if not names or any(n.strip().lower() == "all" for n in names):
        return catalog

    wanted = {n.strip() for n in names if n.strip()}
    keys = {s.key for s in catalog}
    selected: list[NeevScenario] = []
    seen: set[str] = set()
    for token in wanted:
        if token in _GROUP_ALIASES:
            for s in catalog:
                if s.group == token and s.key not in seen:
                    selected.append(s)
                    seen.add(s.key)
        elif token in keys:
            for s in catalog:
                if s.key == token and s.key not in seen:
                    selected.append(s)
                    seen.add(s.key)
        else:
            valid_keys = ", ".join(sorted(keys))
            valid_groups = ", ".join(sorted(_GROUP_ALIASES))
            raise ValueError(
                f"Unknown --profiles token {token!r}. "
                f"Valid keys: {valid_keys}. Valid groups: {valid_groups}. Or 'all'.")
    # Preserve catalog order for stable reporting.
    order = {s.key: i for i, s in enumerate(catalog)}
    return sorted(selected, key=lambda s: order[s.key])
