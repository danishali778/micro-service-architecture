from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Principal:
    subject_id: str
    tenant_id: str
    scopes: frozenset[str]


@dataclass(frozen=True, slots=True)
class TrustedRequestContext:
    principal: Principal
    correlation_id: str
