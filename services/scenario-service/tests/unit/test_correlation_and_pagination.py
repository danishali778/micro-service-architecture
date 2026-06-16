import pytest
from app.core.exceptions import ValidationFailedError
from app.domain.value_objects.correlation_id import CorrelationId
from app.domain.value_objects.pagination import decode_offset_cursor, encode_offset_cursor


def test_accepts_safe_correlation_id() -> None:
    assert CorrelationId.from_untrusted("abc.DEF-123").value == "abc.DEF-123"


def test_generates_correlation_id_for_unsafe_input() -> None:
    generated = CorrelationId.from_untrusted("../bad").value

    assert generated != "../bad"
    assert generated


def test_round_trips_offset_cursor() -> None:
    cursor = encode_offset_cursor(75)

    assert decode_offset_cursor(cursor) == 75


def test_rejects_malformed_cursor() -> None:
    with pytest.raises(ValidationFailedError):
        decode_offset_cursor("not-a-valid-offset")
