from dataclasses import dataclass


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
