import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.application.ports.internal_auth import InternalAuthenticator
from app.core.exceptions import BadGatewayError, GatewayTimeoutError, ServiceUnavailableError
from app.domain.scenarios import Scenario, ScenarioPage
from app.domain.value_objects.tenant_context import TrustedRequestContext


class _ScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    name: str
    version: int = Field(ge=1)
    description: str | None = None


class _ScenarioPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_ScenarioResponse]
    next_cursor: str | None

    def to_domain(self) -> ScenarioPage:
        return ScenarioPage(
            items=tuple(
                Scenario(
                    scenario_id=item.scenario_id,
                    name=item.name,
                    version=item.version,
                    description=item.description,
                )
                for item in self.items
            ),
            next_cursor=self.next_cursor,
        )


class ScenarioHttpClient:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        base_url: str,
        authenticator: InternalAuthenticator,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._authenticator = authenticator

    async def list_scenarios(
        self,
        *,
        limit: int,
        cursor: str | None,
        context: TrustedRequestContext,
    ) -> ScenarioPage:
        params: dict[str, str | int] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor

        try:
            response = await self._http_client.get(
                f"{self._base_url}/internal/scenarios",
                params=params,
                headers=self._authenticator.headers(context),
            )
        except httpx.TimeoutException as error:
            raise GatewayTimeoutError() from error
        except httpx.RequestError as error:
            raise ServiceUnavailableError() from error

        if response.status_code >= 500:
            raise ServiceUnavailableError()
        if response.status_code != 200:
            raise BadGatewayError()

        try:
            return _ScenarioPageResponse.model_validate_json(response.content).to_domain()
        except ValidationError as error:
            raise BadGatewayError() from error
