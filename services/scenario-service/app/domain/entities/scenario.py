from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ScenarioCatalogItem:
    id: str
    latest_version: str
    title: str
    summary: str
    difficulty: str
    category: str
    tags: tuple[str, ...]
    estimated_duration_minutes: int
    status: str


@dataclass(frozen=True, slots=True)
class ScenarioPage:
    items: tuple[ScenarioCatalogItem, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class ScenarioSnapshot:
    snapshot_id: str
    scenario_id: str
    version: str
    title: str
    target_profile: dict[str, Any]
    runtime_template: dict[str, Any]
    action_policy: dict[str, Any]
    resource_budget: dict[str, Any]
    verification_contract: dict[str, Any]
