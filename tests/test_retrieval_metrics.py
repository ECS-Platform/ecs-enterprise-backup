"""Tests for the offline retrieval-metrics evaluation harness (ML/RAG review).

Verifies recall/precision/hit-rate/MRR/AP/NDCG against hand-computed values,
the aggregate evaluator, and the golden-set loader. Pure/offline.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from ecs_platform.llm_engine import retrieval_metrics as rm

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "benchmarks" / "config" / "rag_golden_set.json"


# --------------------------------------------------------------------------- #
# Per-metric correctness (hand-computed)
# --------------------------------------------------------------------------- #
def test_recall_at_k():
    # relevant = {A,B,C}; top-3 retrieved = [A,X,B] -> 2 of 3 relevant found.
    assert rm.recall_at_k(["A", "X", "B", "Y"], ["A", "B", "C"], 3) == pytest.approx(2 / 3)


def test_recall_empty_relevant_is_zero():
    assert rm.recall_at_k(["A"], [], 3) == 0.0


def test_precision_at_k():
    # top-4 = [A,X,B,Y]; 2 relevant of 4 retrieved -> 0.5
    assert rm.precision_at_k(["A", "X", "B", "Y"], ["A", "B", "C"], 4) == pytest.approx(0.5)


def test_hit_rate_at_k():
    assert rm.hit_rate_at_k(["X", "A"], ["A"], 3) == 1.0
    assert rm.hit_rate_at_k(["X", "Y"], ["A"], 3) == 0.0


def test_reciprocal_rank():
    # first relevant (B) at rank 2 -> 1/2
    assert rm.reciprocal_rank_at_k(["X", "B", "A"], ["A", "B"], 5) == pytest.approx(0.5)
    # no relevant in top-k -> 0
    assert rm.reciprocal_rank_at_k(["X", "Y"], ["A"], 2) == 0.0


def test_average_precision():
    # retrieved [A,X,B]; relevant {A,B}: hit@1 -> 1/1, hit@3 -> 2/3; AP = (1 + 0.667)/2
    ap = rm.average_precision_at_k(["A", "X", "B"], ["A", "B"], 3)
    assert ap == pytest.approx((1.0 + (2 / 3)) / 2)


def test_ndcg_perfect_ranking_is_one():
    # All relevant docs first -> NDCG == 1.0
    assert rm.ndcg_at_k(["A", "B", "X"], ["A", "B"], 3) == pytest.approx(1.0)


def test_ndcg_matches_manual_computation():
    # retrieved [X,A,B]; relevant {A,B}; k=3
    # DCG = 1/log2(3) + 1/log2(4); IDCG = 1/log2(2) + 1/log2(3)
    dcg = 1 / math.log2(3) + 1 / math.log2(4)
    idcg = 1 / math.log2(2) + 1 / math.log2(3)
    assert rm.ndcg_at_k(["X", "A", "B"], ["A", "B"], 3) == pytest.approx(dcg / idcg)


def test_ndcg_no_relevant_is_zero():
    assert rm.ndcg_at_k(["X", "Y"], ["A"], 3) == 0.0


# --------------------------------------------------------------------------- #
# Aggregate evaluation
# --------------------------------------------------------------------------- #
def test_evaluate_aggregate_macro_average():
    results = [
        rm.QueryResult("q1", retrieved=["A", "B"], relevant=["A"]),   # perfect@1
        rm.QueryResult("q2", retrieved=["X", "A"], relevant=["A"]),   # rank 2
    ]
    ev = rm.evaluate(results, k_values=(1, 3))
    assert ev.num_queries == 2
    # hit_rate@3 is 1.0 for both -> 1.0
    assert ev.aggregate["hit_rate@3"] == pytest.approx(1.0)
    # mrr@3 = mean(1.0, 0.5) = 0.75
    assert ev.aggregate["mrr@3"] == pytest.approx(0.75)
    # recall@1 = mean(1.0, 0.0) = 0.5
    assert ev.aggregate["recall@1"] == pytest.approx(0.5)
    assert len(ev.per_query) == 2
    d = ev.to_dict()
    assert d["num_queries"] == 2 and "aggregate" in d


def test_evaluate_empty_is_safe():
    ev = rm.evaluate([], k_values=(1, 5))
    assert ev.num_queries == 0
    assert ev.aggregate == {}


# --------------------------------------------------------------------------- #
# Golden set
# --------------------------------------------------------------------------- #
def test_golden_set_exists_and_well_formed():
    assert GOLDEN.exists(), "golden retrieval set missing"
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 10
    for item in data:
        assert item["query_id"]
        assert item["query"]
        assert isinstance(item["relevant"], list) and item["relevant"]


def test_load_golden_set_parses_into_query_results():
    qs = rm.load_golden_set(str(GOLDEN))
    assert len(qs) >= 10
    assert all(isinstance(q, rm.QueryResult) for q in qs)
    assert all(q.query_id and q.relevant for q in qs)
    # retrieved is empty until a retriever fills it — scoring an empty retrieval
    # yields zero metrics (perfect-miss baseline), never an error.
    ev = rm.evaluate(qs, k_values=(5,))
    assert ev.aggregate["recall@5"] == 0.0


def test_scoring_golden_with_perfect_retrieval():
    # Fill each query's retrieved with its own relevant docs -> all metrics 1.0.
    qs = rm.load_golden_set(str(GOLDEN))
    for q in qs:
        q.retrieved = list(q.relevant)
    ev = rm.evaluate(qs, k_values=(10,))
    assert ev.aggregate["recall@10"] == pytest.approx(1.0)
    assert ev.aggregate["ndcg@10"] == pytest.approx(1.0)
    assert ev.aggregate["hit_rate@10"] == pytest.approx(1.0)
