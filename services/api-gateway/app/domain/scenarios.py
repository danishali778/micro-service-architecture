from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Scenario:
    scenario_id: str
    name: str
    version: int
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ScenarioPage:
    items: tuple[Scenario, ...]
    next_cursor: str | None
