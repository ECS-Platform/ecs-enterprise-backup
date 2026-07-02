"""Evidence lineage (Phase 2 of 5.4).

Builds a deterministic lineage graph over the chain:

    Framework -> Control -> Observation -> Evidence -> Version

from data ECS already holds (observation registry rows, evidence records, version
histories). NO graph database — an in-memory adjacency model only. Supports
ancestor lookup, descendant lookup, and impact analysis.

  * READ-ONLY, NO-LLM, NO schema change.
  * FLAG-GATED by EVIDENCE_LINEAGE_ENABLED (default off).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.evidence_intel._common import flag_enabled
from app.evidence_intel.models import (
    LineageGraph,
    LineageNode,
    LineageRecord,
    LineageSummary,
)

_ORDER = ["framework", "control", "observation", "evidence", "version"]


def lineage_enabled() -> bool:
    return flag_enabled("EVIDENCE_LINEAGE_ENABLED", "lineage_enabled")


def _add_node(graph: LineageGraph, node_type: str, node_id: str, label: str = "",
              **attrs: Any) -> LineageNode:
    node = LineageNode(node_type=node_type, node_id=str(node_id),
                       label=label or str(node_id), attributes=dict(attrs))
    graph.nodes.setdefault(node.key, node)
    return graph.nodes[node.key]


def _add_edge(graph: LineageGraph, parent: LineageNode, child: LineageNode,
              relation: str = "contains") -> None:
    rec = LineageRecord(parent_type=parent.node_type, parent_id=parent.node_id,
                        child_type=child.node_type, child_id=child.node_id,
                        relation=relation)
    if not any(e.parent_key == rec.parent_key and e.child_key == rec.child_key
               for e in graph.edges):
        graph.edges.append(rec)


def build_lineage_graph(observations: Iterable[Mapping[str, Any]], *,
                        version_histories: Mapping[str, Any] | None = None,
                        force: bool = False) -> LineageGraph:
    """Build the lineage graph from observation rows.

    Each observation row may carry: framework, control_id/control, observation_id,
    evidence_id/upload_filename, application. ``version_histories`` optionally maps
    evidence_id -> EvidenceVersionHistory to attach version nodes. Never raises.
    """
    if not force and not lineage_enabled():
        return LineageGraph(enabled=False,
                            note="lineage disabled (EVIDENCE_LINEAGE_ENABLED=false)")
    graph = LineageGraph(enabled=True)
    try:
        version_histories = version_histories or {}
        for obs in observations or []:
            if not isinstance(obs, Mapping):
                continue
            framework = str(obs.get("framework") or "").strip()
            control = str(obs.get("control_id") or obs.get("control") or "").strip()
            obs_id = str(obs.get("observation_id") or "").strip()
            ev_id = str(obs.get("evidence_id") or obs.get("upload_filename") or "").strip()

            fw_node = _add_node(graph, "framework", framework) if framework else None
            ctl_node = _add_node(graph, "control", control,
                                 attributes_framework=framework) if control else None
            obs_node = _add_node(graph, "observation", obs_id,
                                 status=obs.get("status", ""),
                                 application=obs.get("application", "")) if obs_id else None
            ev_node = _add_node(graph, "evidence", ev_id) if ev_id else None

            if fw_node and ctl_node:
                _add_edge(graph, fw_node, ctl_node)
            if ctl_node and obs_node:
                _add_edge(graph, ctl_node, obs_node)
            if obs_node and ev_node:
                _add_edge(graph, obs_node, ev_node)

            if ev_node and ev_id in version_histories:
                hist = version_histories[ev_id]
                versions = getattr(hist, "versions", None) or []
                for v in versions:
                    vnum = getattr(v, "version_number", None)
                    if vnum is None:
                        continue
                    v_node = _add_node(graph, "version", f"{ev_id}#v{vnum}",
                                       label=f"v{vnum}",
                                       status=getattr(v, "evidence_status", ""))
                    _add_edge(graph, ev_node, v_node, relation="has_version")
        return graph
    except Exception:  # noqa: BLE001 - fail safe
        return LineageGraph(enabled=False, note="lineage error (ignored)")


# --------------------------------------------------------------------------- #
# Traversal: ancestors / descendants / impact
# --------------------------------------------------------------------------- #

def _children(graph: LineageGraph, key: str) -> list[str]:
    return [e.child_key for e in graph.edges if e.parent_key == key]


def _parents(graph: LineageGraph, key: str) -> list[str]:
    return [e.parent_key for e in graph.edges if e.child_key == key]


def descendants(graph: LineageGraph, key: str) -> list[str]:
    """All transitive descendants of a node (deterministic, cycle-safe)."""
    seen: list[str] = []
    stack = list(_children(graph, key))
    while stack:
        cur = stack.pop(0)
        if cur in seen:
            continue
        seen.append(cur)
        stack.extend(_children(graph, cur))
    return seen


def ancestors(graph: LineageGraph, key: str) -> list[str]:
    """All transitive ancestors of a node (deterministic, cycle-safe)."""
    seen: list[str] = []
    stack = list(_parents(graph, key))
    while stack:
        cur = stack.pop(0)
        if cur in seen:
            continue
        seen.append(cur)
        stack.extend(_parents(graph, cur))
    return seen


def impact_analysis(graph: LineageGraph, key: str) -> dict[str, list[str]]:
    """What is affected if ``key`` changes: its descendants grouped by node type."""
    out: dict[str, list[str]] = {t: [] for t in _ORDER}
    for dk in descendants(graph, key):
        node = graph.nodes.get(dk)
        if node and node.node_type in out:
            out[node.node_type].append(node.node_id)
    return out


def summarize(graph: LineageGraph, root_key: str) -> LineageSummary:
    """Summarize the lineage reachable from a root node."""
    summary = LineageSummary(root_key=root_key)
    try:
        keys = [root_key] + descendants(graph, root_key)
        for k in keys:
            node = graph.nodes.get(k)
            if not node:
                continue
            bucket = {
                "framework": summary.frameworks, "control": summary.controls,
                "observation": summary.observations, "evidence": summary.evidence,
                "version": summary.versions,
            }.get(node.node_type)
            if bucket is not None and node.node_id not in bucket:
                bucket.append(node.node_id)
        summary.descendant_count = len(descendants(graph, root_key))
        summary.ancestor_count = len(ancestors(graph, root_key))
        return summary
    except Exception:  # noqa: BLE001
        return summary
