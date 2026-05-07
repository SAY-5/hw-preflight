"""HMAC-signed webhook delivery for hw-preflight reports.

The webhook payload is the JSON serialization produced by
:func:`hw_preflight.reports.to_json`. The signature is HMAC-SHA256 of the
payload using a secret read from the ``HW_PREFLIGHT_WEBHOOK_SECRET``
environment variable, hex-encoded, and supplied in the
``X-HW-Preflight-Signature`` header (with a ``sha256=`` prefix to match
the convention used by GitHub and Stripe).

A secondary ``X-HW-Preflight-Timestamp`` header records the unix epoch
seconds at which the request was prepared; receivers can reject replays
older than their window.

Networking uses the standard library's ``urllib`` so that webhooks ship
with zero new dependencies.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .reports import to_json
from .runner import RunReport

ENV_SECRET = "HW_PREFLIGHT_WEBHOOK_SECRET"
SIGNATURE_HEADER = "X-HW-Preflight-Signature"
TIMESTAMP_HEADER = "X-HW-Preflight-Timestamp"


@dataclass
class SignedRequest:
    """The payload and headers prepared for delivery, exposed for tests."""

    body: bytes
    signature_header: str
    timestamp_header: str
    url: str


def _resolve_secret(secret: str | None) -> str:
    if secret is not None:
        return secret
    env = os.environ.get(ENV_SECRET)
    if not env:
        raise RuntimeError(
            f"webhook delivery requires {ENV_SECRET} to be set " "(or pass secret= explicitly)"
        )
    return env


def sign_payload(payload: bytes, secret: str) -> str:
    """Return the ``sha256=<hex>`` signature header value for ``payload``."""
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def prepare_request(
    report: RunReport,
    url: str,
    *,
    secret: str | None = None,
    timestamp: int | None = None,
) -> SignedRequest:
    """Build the body+headers for a webhook delivery without sending it.

    Exposed so tests can verify the signature shape independent of any
    network plumbing.
    """
    secret_value = _resolve_secret(secret)
    body = to_json(report).encode("utf-8")
    sig_header = sign_payload(body, secret_value)
    ts = timestamp if timestamp is not None else int(time.time())
    return SignedRequest(
        body=body,
        signature_header=sig_header,
        timestamp_header=str(ts),
        url=url,
    )


def deliver(
    report: RunReport,
    url: str,
    *,
    secret: str | None = None,
    timeout: float = 5.0,
    timestamp: int | None = None,
) -> int:
    """POST ``report`` to ``url`` with HMAC-SHA256 signing.

    Returns the HTTP status code. Network errors raise
    :class:`urllib.error.URLError`; the caller decides how to log/exit.
    """
    prepared = prepare_request(report, url, secret=secret, timestamp=timestamp)
    req = urllib.request.Request(
        prepared.url,
        data=prepared.body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "hw-preflight/0.1",
            SIGNATURE_HEADER: prepared.signature_header,
            TIMESTAMP_HEADER: prepared.timestamp_header,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(resp.status)


__all__ = [
    "ENV_SECRET",
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "SignedRequest",
    "deliver",
    "prepare_request",
    "sign_payload",
]
