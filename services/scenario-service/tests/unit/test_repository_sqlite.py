from app.infrastructure.database.repositories import SqlAlchemyScenarioRepository
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def test_repository_filters_latest_published_visible_rows_without_postgres() -> None:
    engine = create_engine("sqlite:///:memory:")
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE scenarios (
                  scenario_id VARCHAR PRIMARY KEY,
                  title VARCHAR NOT NULL,
                  summary VARCHAR NOT NULL,
                  difficulty VARCHAR NOT NULL,
                  category VARCHAR NOT NULL,
                  tags JSON NOT NULL,
                  visibility VARCHAR NOT NULL,
                  owner_tenant_id VARCHAR,
                  estimated_duration_minutes INTEGER NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE scenario_versions (
                  scenario_version_id VARCHAR PRIMARY KEY,
                  scenario_id VARCHAR NOT NULL,
                  version VARCHAR NOT NULL,
                  status VARCHAR NOT NULL,
                  published_at VARCHAR
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO scenarios (
                  scenario_id,
                  title,
                  summary,
                  difficulty,
                  category,
                  tags,
                  visibility,
                  owner_tenant_id,
                  estimated_duration_minutes
                )
                VALUES (
                  :scenario_id,
                  :title,
                  'Summary',
                  'beginner',
                  'web',
                  '[]',
                  :visibility,
                  :owner_tenant_id,
                  30
                )
                """
            ),
            [
                {
                    "scenario_id": "public-one",
                    "title": "Public One",
                    "visibility": "public",
                    "owner_tenant_id": None,
                },
                {
                    "scenario_id": "private-one",
                    "title": "Private One",
                    "visibility": "private",
                    "owner_tenant_id": "tenant-1",
                },
                {
                    "scenario_id": "private-two",
                    "title": "Private Two",
                    "visibility": "private",
                    "owner_tenant_id": "tenant-2",
                },
            ],
        )
        connection.execute(
            text(
                """
                INSERT INTO scenario_versions (
                  scenario_version_id,
                  scenario_id,
                  version,
                  status,
                  published_at
                )
                VALUES (
                  :scenario_version_id,
                  :scenario_id,
                  :version,
                  'published',
                  :published_at
                )
                """
            ),
            [
                {
                    "scenario_version_id": "public-one-1",
                    "scenario_id": "public-one",
                    "version": "1.0.0",
                    "published_at": "2026-01-01T00:00:00Z",
                },
                {
                    "scenario_version_id": "public-one-2",
                    "scenario_id": "public-one",
                    "version": "1.1.0",
                    "published_at": "2026-02-01T00:00:00Z",
                },
                {
                    "scenario_version_id": "private-one-1",
                    "scenario_id": "private-one",
                    "version": "1.0.0",
                    "published_at": "2026-01-01T00:00:00Z",
                },
                {
                    "scenario_version_id": "private-two-1",
                    "scenario_id": "private-two",
                    "version": "1.0.0",
                    "published_at": "2026-01-01T00:00:00Z",
                },
            ],
        )

    try:
        repository = SqlAlchemyScenarioRepository(factory)
        page = repository.list_visible_published(tenant_id="tenant-1", limit=1, offset=0)
    finally:
        engine.dispose()

    assert [item.id for item in page.items] == ["private-one"]
    assert page.items[0].latest_version == "1.0.0"
    assert page.next_cursor is not None
