from typing import cast

from fastapi import Request

from app.core.container import Services


def get_services(request: Request) -> Services:
    return cast(Services, request.app.state.services)
