"""Unit tests for modules/operations/engines/sonarqube_connector.py."""

from __future__ import annotations

import base64
import io
import json
from unittest.mock import MagicMock, patch

import pytest
import urllib.error

from modules.operations.engines.sonarqube_connector import SonarQubeConnector


def _mock_response(payload: dict | str, *, status: int = 200) -> MagicMock:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8")
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _http_error(code: int, body: str = "") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "http://sonarqube-demo:9000/api/test",
        code,
        "Error",
        {},
        io.BytesIO(body.encode("utf-8")),
    )


def test_connect_health_uses_no_auth():
    captured: dict[str, str] = {}

    def fake_urlopen(req, timeout=None):
        captured["auth"] = req.get_header("Authorization") or ""
        return _mock_response({"status": "UP"})

    connector = SonarQubeConnector(
        base_url="http://sonarqube-demo:9000",
        user="admin",
        password="wrong-password",
        token="",
    )
    with patch("urllib.request.urlopen", fake_urlopen):
        assert connector.connect() is True
    assert captured["auth"] == ""


def test_token_auth_is_basic_not_bearer():
    captured: dict[str, str] = {}

    def fake_urlopen(req, timeout=None):
        captured["auth"] = req.get_header("Authorization") or ""
        return _mock_response({"paging": {"total": 2}, "components": []})

    connector = SonarQubeConnector(base_url="http://sonarqube-demo:9000", token="SQTOKEN")
    with patch("urllib.request.urlopen", fake_urlopen):
        connector.connect()
        connector.execute("projects")

    assert captured["auth"].startswith("Basic ")
    assert base64.b64decode(captured["auth"].split()[1]).decode() == "SQTOKEN:"


@pytest.mark.parametrize(
    "side_effect, expected_type, expected_snippet",
    [
        (
            urllib.error.URLError("Connection refused"),
            "connection_failure",
            "not reachable",
        ),
        (
            urllib.error.URLError("timed out"),
            "connection_failure",
            "timed out",
        ),
        (
            _http_error(401, '{"errors":[{"msg":"Unauthorized"}]}'),
            "authentication_failure",
            "authentication failed",
        ),
    ],
)
def test_connect_classifies_failures(side_effect, expected_type, expected_snippet):
    connector = SonarQubeConnector(base_url="http://sonarqube-demo:9000")
    with patch("urllib.request.urlopen", side_effect=side_effect):
        assert connector.connect() is False
    assert connector._last_error_type == expected_type
    assert expected_snippet.lower() in connector._last_error.lower()


def test_connect_invalid_json_is_response_validation_failure():
    def fake_urlopen(req, timeout=None):
        return _mock_response("not-json")

    connector = SonarQubeConnector(base_url="http://sonarqube-demo:9000")
    with patch("urllib.request.urlopen", fake_urlopen):
        assert connector.connect() is False
    assert connector._last_error_type == "response_validation_failure"


@pytest.mark.parametrize(
    "code, expected_type, expected_snippet",
    [
        (401, "authentication_failure", "authentication failed"),
        (403, "query_failure", "authorization denied"),
        (404, "query_failure", "endpoint not found"),
        (500, "remote_service_failure", "server error"),
    ],
)
def test_execute_preserves_endpoint_http_failures(code, expected_type, expected_snippet):
    connector = SonarQubeConnector(base_url="http://sonarqube-demo:9000", token="tok")
    with patch("urllib.request.urlopen", side_effect=_http_error(code, "detail")):
        result = connector.execute("projects")
    assert result.success is False
    assert result.metadata["error_type"] == expected_type
    assert expected_snippet in result.error_message.lower()


def test_execute_invalid_json_is_response_validation_failure():
    connector = SonarQubeConnector(base_url="http://sonarqube-demo:9000", token="tok")

    def fake_urlopen(req, timeout=None):
        return _mock_response("still-not-json")

    with patch("urllib.request.urlopen", fake_urlopen):
        result = connector.execute("projects")
    assert result.success is False
    assert result.metadata["error_type"] == "response_validation_failure"
