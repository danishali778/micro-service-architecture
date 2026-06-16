import re
from dataclasses import dataclass
from uuid import uuid4

_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True, slots=True)
class CorrelationId:
    value: str

    @classmethod
    def from_untrusted(cls, raw_value: str | None) -> "CorrelationId":
        if raw_value is not None and _SAFE_CORRELATION_ID.fullmatch(raw_value) is not None:
            return cls(raw_value)
        return cls(str(uuid4()))
