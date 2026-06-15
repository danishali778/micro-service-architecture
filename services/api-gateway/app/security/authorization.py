from app.core.exceptions import ForbiddenError
from app.domain.value_objects.tenant_context import Principal


def require_scope(principal: Principal, scope: str) -> None:
    if scope not in principal.scopes:
        raise ForbiddenError()
