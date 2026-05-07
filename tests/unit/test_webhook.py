"""Tests for the HMAC-signed webhook output mode."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

import pytest

from hw_preflight import webhook
from hw_preflight.checks._base import CheckResult
from hw_preflight.runner import HostInfo, RunReport


def _sample_report() -> RunReport:
    now = datetime.now(UTC).isoformat()
    return RunReport(
        started_at=now,
        finished_at=now,
        host=HostInfo(hostname="h", kernel="k", cpu_count=2),
        checks=[CheckResult(name="cpu_count", status="pass")],
    )


def test_sign_payload_is_deterministic_and_hex() -> None:
    sig = webhook.sign_payload(b"abc", "topsecret")
    expected = hmac.new(b"topsecret", b"abc", hashlib.sha256).hexdigest()
    assert sig == f"sha256={expected}"


def test_sign_payload_changes_with_secret() -> None:
    a = webhook.sign_payload(b"abc", "secretA")
    b = webhook.sign_payload(b"abc", "secretB")
    assert a != b


def test_prepare_request_includes_signature_and_timestamp() -> None:
    report = _sample_report()
    prepared = webhook.prepare_request(
        report,
        "https://example.test/hook",
        secret="topsecret",
        timestamp=1700000000,
    )
    # Body parses as the JSON serialization of the report.
    parsed = json.loads(prepared.body.decode("utf-8"))
    assert parsed["summary"]["total"] == 1
    # Signature is verifiable.
    digest = hmac.new(b"topsecret", prepared.body, hashlib.sha256).hexdigest()
    assert prepared.signature_header == f"sha256={digest}"
    assert prepared.timestamp_header == "1700000000"
    assert prepared.url == "https://example.test/hook"


def test_prepare_request_uses_env_secret_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(webhook.ENV_SECRET, "from-env")
    prepared = webhook.prepare_request(_sample_report(), "https://x.example/hook")
    digest = hmac.new(b"from-env", prepared.body, hashlib.sha256).hexdigest()
    assert prepared.signature_header == f"sha256={digest}"


def test_prepare_request_raises_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(webhook.ENV_SECRET, raising=False)
    with pytest.raises(RuntimeError, match=webhook.ENV_SECRET):
        webhook.prepare_request(_sample_report(), "https://x.example/hook")


def test_deliver_posts_with_signed_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Capture the urllib request and verify all signing fields are present.

    A signed receiver re-computes HMAC(body, secret) and compares against
    the header; we replicate that check to prove the round-trip works.
    """
    captured: dict[str, Any] = {}

    class FakeResponse:
        status = 202

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def fake_urlopen(req: Any, timeout: float = 5.0) -> FakeResponse:
        captured["url"] = req.full_url
        captured["data"] = req.data
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        captured["method"] = req.get_method()
        return FakeResponse()

    monkeypatch.setattr(webhook.urllib.request, "urlopen", fake_urlopen)

    status = webhook.deliver(
        _sample_report(),
        "https://hooks.example.test/abc",
        secret="my-shared-secret",
        timestamp=1700001234,
    )
    assert status == 202
    assert captured["url"] == "https://hooks.example.test/abc"
    assert captured["method"] == "POST"

    # Headers — note that urllib title-cases keys.
    assert captured["headers"]["content-type"] == "application/json"
    assert captured["headers"]["x-hw-preflight-timestamp"] == "1700001234"
    sig_header = captured["headers"]["x-hw-preflight-signature"]
    expected = hmac.new(b"my-shared-secret", captured["data"], hashlib.sha256).hexdigest()
    assert sig_header == f"sha256={expected}"


def test_signature_constants_are_unchanged() -> None:
    """Header names are part of the public contract; pin them."""
    assert webhook.SIGNATURE_HEADER == "X-HW-Preflight-Signature"
    assert webhook.TIMESTAMP_HEADER == "X-HW-Preflight-Timestamp"
    assert webhook.ENV_SECRET == "HW_PREFLIGHT_WEBHOOK_SECRET"
