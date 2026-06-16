from typing import cast

from sqlalchemy import text
from sqlalchemy.engine import RowMapping

from app.domain.entities.scenario import ScenarioCatalogItem, ScenarioPage
from app.domain.value_objects.pagination import encode_offset_cursor
from app.infrastructure.database.connection import SessionFactory


class SqlAlchemyScenarioRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def list_visible_published(
        self,
        *,
        tenant_id: str,
        limit: int,
        offset: int,
    ) -> ScenarioPage:
        query = text(
            """
            WITH latest_versions AS (
              SELECT
                sv.scenario_id,
                sv.version,
                sv.status,
                ROW_NUMBER() OVER (
                  PARTITION BY sv.scenario_id
                  ORDER BY sv.published_at DESC NULLS LAST, sv.version DESC
                ) AS row_number
              FROM scenario_versions sv
              WHERE sv.status = 'published'
            )
            SELECT
              s.scenario_id AS id,
              latest_versions.version AS latest_version,
              s.title,
              s.summary,
              s.difficulty,
              s.category,
              s.tags,
              s.estimated_duration_minutes,
              latest_versions.status
            FROM scenarios s
            JOIN latest_versions
              ON latest_versions.scenario_id = s.scenario_id
             AND latest_versions.row_number = 1
            WHERE
              s.visibility = 'public'
              OR (s.visibility = 'private' AND s.owner_tenant_id = :tenant_id)
            ORDER BY s.title ASC, s.scenario_id ASC
            LIMIT :limit_plus_one
            OFFSET :offset
            """
        )

        with self._session_factory() as session:
            rows = list(
                session.execute(
                    query,
                    {
                        "tenant_id": tenant_id,
                        "limit_plus_one": limit + 1,
                        "offset": offset,
                    },
                )
                .mappings()
                .all()
            )

        visible_rows = rows[:limit]
        return ScenarioPage(
            items=tuple(_row_to_catalog_item(row) for row in visible_rows),
            next_cursor=encode_offset_cursor(offset + limit) if len(rows) > limit else None,
        )


def _row_to_catalog_item(row: RowMapping) -> ScenarioCatalogItem:
    raw_tags = cast(object, row["tags"])
    tags = (
        tuple(item for item in raw_tags if isinstance(item, str))
        if isinstance(raw_tags, list)
        else ()
    )
    return ScenarioCatalogItem(
        id=str(row["id"]),
        latest_version=str(row["latest_version"]),
        title=str(row["title"]),
        summary=str(row["summary"]),
        difficulty=str(row["difficulty"]),
        category=str(row["category"]),
        tags=tags,
        estimated_duration_minutes=int(row["estimated_duration_minutes"]),
        status=str(row["status"]),
    )
