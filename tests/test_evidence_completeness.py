"""Unit tests for Phase 2 Evidence Completeness Detection service."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from ecs_platform.evidence_completeness import (
    STATUS_COMPLETE,
    STATUS_MISSING,
    STATUS_PARTIAL,
    _classify_evidence_rows,
    compute_evidence_completeness,
)


class _FakeFcmRepo:
    """Minimal FCM stand-in with two controls."""

    def resolve_framework_id(self, framework_id: str) -> str:
        key = (framework_id or "").strip().lower()
        if key in {"pci_dss", "pci-dss", "pci dss"}:
            return "pci_dss"
        return key

    def get_framework(self, framework_id: str):
        if framework_id != "pci_dss":
            return None
        return {
            "framework": {
                "id": "pci_dss",
                "name": "PCI DSS",
                "display_name": "PCI DSS",
            },
            "controls": [
                {"id": "PCI-C-01", "title": "Network Segmentation", "domain": "Network"},
                {"id": "PCI-C-02", "title": "Encryption at Rest", "domain": "Cryptography"},
                {"id": "PCI-C-03", "title": "Encryption in Transit", "domain": "Cryptography"},
            ],
        }

    def list_framework_summaries(self):
        return [
            {
                "id": "pci_dss",
                "code": "PCI-DSS",
                "name": "PCI DSS",
                "display_name": "PCI DSS",
            }
        ]


def test_classify_missing_when_no_rows():
    status, detail = _classify_evidence_rows([])
    assert status == STATUS_MISSING
    assert detail["evidence_count"] == 0


def test_classify_complete_when_approved_and_fresh():
    status, detail = _classify_evidence_rows(
        [{"evidence_uid": "EVD-1", "review_status": "Approved", "valid_until": None}]
    )
    assert status == STATUS_COMPLETE
    assert detail["evidence_uids"] == ["EVD-1"]


def test_classify_complete_accepts_accepted_alias():
    status, _ = _classify_evidence_rows(
        [{"evidence_uid": "EVD-1", "review_status": "Accepted", "valid_until": None}]
    )
    assert status == STATUS_COMPLETE


def test_classify_partial_when_pending():
    status, _ = _classify_evidence_rows(
        [{"evidence_uid": "EVD-1", "review_status": "UnderReview", "valid_until": None}]
    )
    assert status == STATUS_PARTIAL


def test_classify_partial_when_rejected():
    status, _ = _classify_evidence_rows(
        [{"evidence_uid": "EVD-1", "review_status": "Rejected", "valid_until": None}]
    )
    assert status == STATUS_PARTIAL


def test_classify_partial_when_expired_status():
    status, _ = _classify_evidence_rows(
        [{"evidence_uid": "EVD-1", "review_status": "Expired", "valid_until": None}]
    )
    assert status == STATUS_PARTIAL


def test_classify_partial_when_approved_but_past_valid_until():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    status, _ = _classify_evidence_rows(
        [{"evidence_uid": "EVD-1", "review_status": "Approved", "valid_until": past}],
        now=datetime.now(timezone.utc),
    )
    assert status == STATUS_PARTIAL


def test_classify_complete_wins_among_mixed_rows():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    status, detail = _classify_evidence_rows(
        [
            {"evidence_uid": "EVD-old", "review_status": "Expired", "valid_until": past},
            {"evidence_uid": "EVD-ok", "review_status": "Approved", "valid_until": None},
        ]
    )
    assert status == STATUS_COMPLETE
    assert detail["evidence_count"] == 2


def test_compute_completeness_summary(monkeypatch):
    by_control = {
        "PCI-C-01": [
            {"evidence_uid": "EVD-1", "review_status": "Approved", "valid_until": None}
        ],
        "PCI-C-02": [
            {"evidence_uid": "EVD-2", "review_status": "UnderReview", "valid_until": None}
        ],
        "PCI-C-03": [],
    }

    def _fake_fetch(repo, *, application, control_ids):
        assert application == "Net Banking"
        return by_control, {}

    monkeypatch.setattr(
        "ecs_platform.evidence_completeness._fetch_evidence_by_control",
        _fake_fetch,
    )

    result = compute_evidence_completeness(
        "Net Banking",
        "PCI DSS",
        repo=object(),  # unused — fetch is mocked
        fcm_repo=_FakeFcmRepo(),
    )
    assert result["ok"] is True
    assert result["application"] == "Net Banking"
    assert result["framework_id"] == "pci_dss"
    summary = result["summary"]
    assert summary == {
        "total_controls": 3,
        "complete": 1,
        "partial": 1,
        "missing": 1,
        "completeness_pct": 33.3,
    }
    by_id = {c["control_id"]: c for c in result["controls"]}
    assert by_id["PCI-C-01"]["status"] == STATUS_COMPLETE
    assert by_id["PCI-C-01"]["reason"] == "Approved evidence exists"
    assert by_id["PCI-C-02"]["status"] == STATUS_PARTIAL
    assert by_id["PCI-C-02"]["reason"] == "Pending review"
    assert by_id["PCI-C-03"]["status"] == STATUS_MISSING
    assert by_id["PCI-C-03"]["reason"] == "No evidence found"
    assert "readiness" not in result
    assert "score" not in result


def test_compute_requires_application():
    result = compute_evidence_completeness("", "PCI DSS", fcm_repo=_FakeFcmRepo())
    assert result["ok"] is False
    assert "application" in result["error"]


def test_compute_unknown_framework(monkeypatch):
    class _EmptyRepo:
        def connect(self):
            return self

        def cursor(self):
            return self

        def execute(self, *a, **k):
            return None

        def fetchall(self):
            return []

        def close(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    result = compute_evidence_completeness(
        "Net Banking",
        "No Such Framework",
        repo=_EmptyRepo(),
        fcm_repo=_FakeFcmRepo(),
    )
    assert result["ok"] is False
    assert "Unknown framework" in result["error"]


def test_compute_all_complete_is_100_pct(monkeypatch):
    by_control = {
        "PCI-C-01": [{"evidence_uid": "a", "review_status": "Approved", "valid_until": None}],
        "PCI-C-02": [{"evidence_uid": "b", "review_status": "Accepted", "valid_until": None}],
        "PCI-C-03": [{"evidence_uid": "c", "review_status": "Approved", "valid_until": None}],
    }
    monkeypatch.setattr(
        "ecs_platform.evidence_completeness._fetch_evidence_by_control",
        lambda *a, **k: (by_control, {}),
    )
    result = compute_evidence_completeness(
        "Net Banking", "pci_dss", repo=object(), fcm_repo=_FakeFcmRepo()
    )
    assert result["summary"]["completeness_pct"] == 100.0
    assert result["summary"]["missing"] == 0
    assert result["summary"]["partial"] == 0
