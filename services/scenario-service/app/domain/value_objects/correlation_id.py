import re
from dataclasses import dataclass
from uuid import uuid4

_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True, slots=True)
class CorrelationId:
    value: str

    @classmethod
    def from_untrusted(cls, raw_value: str | None) -> "CorrelationId":
        if raw_value and _CORRELATION_ID_PATTERN.fullmatch(raw_value):
            return cls(raw_value)
        return cls(str(uuid4()))
