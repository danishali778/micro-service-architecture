import re
from dataclasses import dataclass
from uuid import uuid4

_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True, slots=True)
class CorrelationId:
    value: str

    @classmethod
    def from_untrusted(cls, candidate: str | None) -> "CorrelationId":
        if candidate is not None and _CORRELATION_ID_PATTERN.fullmatch(candidate):
            return cls(candidate)
        return cls(str(uuid4()))
