"""Offline retrieval-quality metrics for the ECS RAG stack (ML evaluation).

Standard information-retrieval metrics computed against a labeled golden set
(query -> set of relevant document ids). Pure-Python, dependency-free, fully
deterministic and offline — no model, no DB, no network. Complements the
runtime telemetry in ``metrics_logger.py`` (which records latency/token counts
but no relevance quality).

Metrics implemented (all @k):
  * recall@k          — fraction of relevant docs retrieved in the top-k
  * precision@k       — fraction of top-k that are relevant
  * hit_rate@k        — 1.0 if any relevant doc is in the top-k, else 0.0
  * MRR@k             — mean reciprocal rank of the first relevant doc
  * average_precision — AP@k (area under the precision-recall curve, top-k)
  * NDCG@k            — normalized discounted cumulative gain (binary relevance)

A "retrieved" list is an ordered sequence of document ids (most relevant first),
exactly what a vector search / RAG retriever returns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence


def _topk(retrieved: Sequence[str], k: int) -> list[str]:
    if k <= 0:
        return list(retrieved)
    return list(retrieved[:k])


def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Fraction of the relevant docs that appear in the top-k retrieved."""
    rel = set(relevant)
    if not rel:
        return 0.0
    hits = sum(1 for d in _topk(retrieved, k) if d in rel)
    return hits / len(rel)


def precision_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Fraction of the top-k retrieved docs that are relevant."""
    rel = set(relevant)
    top = _topk(retrieved, k)
    if not top:
        return 0.0
    hits = sum(1 for d in top if d in rel)
    return hits / len(top)


def hit_rate_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """1.0 if at least one relevant doc is in the top-k, else 0.0."""
    rel = set(relevant)
    return 1.0 if any(d in rel for d in _topk(retrieved, k)) else 0.0


def reciprocal_rank_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Reciprocal of the rank (1-based) of the first relevant doc in top-k."""
    rel = set(relevant)
    for idx, doc in enumerate(_topk(retrieved, k), start=1):
        if doc in rel:
            return 1.0 / idx
    return 0.0


def average_precision_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Average precision @k (binary relevance): mean of precision at each hit."""
    rel = set(relevant)
    if not rel:
        return 0.0
    top = _topk(retrieved, k)
    hits = 0
    score = 0.0
    for idx, doc in enumerate(top, start=1):
        if doc in rel:
            hits += 1
            score += hits / idx
    denom = min(len(rel), len(top)) or 1
    return score / denom


def ndcg_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Normalized DCG @k with binary relevance (gain 1 for relevant, else 0)."""
    rel = set(relevant)
    top = _topk(retrieved, k)
    dcg = 0.0
    for idx, doc in enumerate(top, start=1):
        if doc in rel:
            dcg += 1.0 / math.log2(idx + 1)
    # Ideal DCG: all relevant docs ranked first (capped at k).
    ideal_hits = min(len(rel), len(top))
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return (dcg / idcg) if idcg > 0 else 0.0


@dataclass
class QueryResult:
    """One evaluation case: a query, its ranked retrieval, and the gold labels."""

    query_id: str
    retrieved: list[str]
    relevant: list[str]

    def metrics(self, k: int) -> dict[str, float]:
        return {
            f"recall@{k}": recall_at_k(self.retrieved, self.relevant, k),
            f"precision@{k}": precision_at_k(self.retrieved, self.relevant, k),
            f"hit_rate@{k}": hit_rate_at_k(self.retrieved, self.relevant, k),
            f"mrr@{k}": reciprocal_rank_at_k(self.retrieved, self.relevant, k),
            f"ap@{k}": average_precision_at_k(self.retrieved, self.relevant, k),
            f"ndcg@{k}": ndcg_at_k(self.retrieved, self.relevant, k),
        }


@dataclass
class RetrievalEvaluation:
    """Aggregate retrieval metrics over a set of query results at several k."""

    k_values: tuple[int, ...] = (1, 3, 5, 10)
    per_query: list[dict] = field(default_factory=list)
    aggregate: dict[str, float] = field(default_factory=dict)
    num_queries: int = 0

    def to_dict(self) -> dict:
        return {
            "num_queries": self.num_queries,
            "k_values": list(self.k_values),
            "aggregate": self.aggregate,
            "per_query": self.per_query,
        }


def evaluate(results: Sequence[QueryResult],
             k_values: Sequence[int] = (1, 3, 5, 10)) -> RetrievalEvaluation:
    """Compute per-query + macro-averaged retrieval metrics at each k.

    ``results`` is a list of :class:`QueryResult`. Returns a
    :class:`RetrievalEvaluation` with per-query breakdowns and the mean of each
    metric across all queries (macro average — every query weighted equally).
    """
    k_values = tuple(int(k) for k in k_values)
    per_query: list[dict] = []
    sums: dict[str, float] = {}
    for res in results:
        row: dict[str, float] = {"query_id": res.query_id}
        for k in k_values:
            m = res.metrics(k)
            row.update(m)
            for name, val in m.items():
                sums[name] = sums.get(name, 0.0) + val
        per_query.append(row)
    n = len(results) or 1
    aggregate = {name: round(total / n, 4) for name, total in sums.items()}
    return RetrievalEvaluation(
        k_values=k_values,
        per_query=per_query,
        aggregate=aggregate,
        num_queries=len(results),
    )


def load_golden_set(path: str) -> list[QueryResult]:
    """Load a labeled golden set (query_id -> relevant ids) as QueryResult stubs.

    The file is a JSON list of objects with ``query_id`` and ``relevant`` (list
    of relevant doc ids); ``retrieved`` is left empty for the caller to fill from
    a live/mock retriever before scoring. Never raises on a missing optional
    ``retrieved`` field.
    """
    import json

    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    out: list[QueryResult] = []
    for item in raw if isinstance(raw, list) else []:
        out.append(QueryResult(
            query_id=str(item.get("query_id", "")),
            retrieved=list(item.get("retrieved", []) or []),
            relevant=list(item.get("relevant", []) or []),
        ))
    return out
