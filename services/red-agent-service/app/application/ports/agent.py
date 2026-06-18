from typing import Protocol

from app.domain.entities.red_run import AttackProposal, RedRunRequest


class RedAgent(Protocol):
    @property
    def is_ready(self) -> bool: ...

    @property
    def adapter_name(self) -> str: ...

    async def generate_proposal(self, request: RedRunRequest) -> AttackProposal: ...
