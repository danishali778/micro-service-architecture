import re

from app.domain.value_objects.correlation_id import CorrelationId


def test_accepts_safe_correlation_id() -> None:
    assert CorrelationId.from_untrusted("client.request-123").value == "client.request-123"


def test_replaces_invalid_correlation_id() -> None:
    value = CorrelationId.from_untrusted("invalid correlation id").value

    assert value != "invalid correlation id"
    assert re.fullmatch(r"[0-9a-f-]{36}", value)
