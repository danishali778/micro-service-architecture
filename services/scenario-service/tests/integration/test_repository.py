from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from app.infrastructure.database.connection import create_session_factory
from app.infrastructure.database.models import ScenarioModel, ScenarioVersionModel
from app.infrastructure.database.repositories import SqlAlchemyScenarioRepository
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def session_factory(
    alembic_config: Config,
    database_test_url: str,
) -> Iterator[sessionmaker[Session]]:
    command.upgrade(alembic_config, "head")
    engine = create_engine(database_test_url)
    factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    with factory() as session:
        session.execute(delete(ScenarioVersionModel))
        session.execute(delete(ScenarioModel))
        session.commit()
    try:
        yield factory
    finally:
        engine.dispose()


def test_repository_lists_latest_published_visible_scenarios(
    session_factory: sessionmaker[Session],
) -> None:
    now = datetime.now(UTC)
    with session_factory() as session:
        _add_scenario(session, "public-old-new", "Public New", "public", None)
        _add_version(session, "public-old-new", "1.0.0", "published", now - timedelta(days=1))
        _add_version(session, "public-old-new", "1.1.0", "published", now)
        _add_scenario(session, "private-owned", "Private Owned", "private", "tenant-1")
        _add_version(session, "private-owned", "1.0.0", "published", now)
        _add_scenario(session, "private-other", "Private Other", "private", "tenant-2")
        _add_version(session, "private-other", "1.0.0", "published", now)
        _add_scenario(session, "draft-only", "Draft Only", "public", None)
        _add_version(session, "draft-only", "1.0.0", "draft", now)
        session.commit()

    repository = SqlAlchemyScenarioRepository(create_session_factory(session_factory.kw["bind"]))

    page = repository.list_visible_published(tenant_id="tenant-1", limit=10, offset=0)

    assert [(item.id, item.latest_version) for item in page.items] == [
        ("private-owned", "1.0.0"),
        ("public-old-new", "1.1.0"),
    ]
    assert page.next_cursor is None


def test_repository_returns_next_cursor_when_more_rows_exist(
    session_factory: sessionmaker[Session],
) -> None:
    now = datetime.now(UTC)
    with session_factory() as session:
        for index in range(3):
            scenario_id = f"public-{index}"
            _add_scenario(session, scenario_id, f"Public {index}", "public", None)
            _add_version(session, scenario_id, "1.0.0", "published", now)
        session.commit()

    repository = SqlAlchemyScenarioRepository(create_session_factory(session_factory.kw["bind"]))

    page = repository.list_visible_published(tenant_id="tenant-1", limit=2, offset=0)

    assert len(page.items) == 2
    assert page.next_cursor is not None


def _add_scenario(
    session: Session,
    scenario_id: str,
    title: str,
    visibility: str,
    owner_tenant_id: str | None,
) -> None:
    session.add(
        ScenarioModel(
            scenario_id=scenario_id,
            slug=scenario_id,
            title=title,
            summary=f"Summary for {title}",
            description=None,
            category="web-security",
            difficulty="beginner",
            tags=["tag"],
            visibility=visibility,
            owner_tenant_id=owner_tenant_id,
            estimated_duration_minutes=30,
        )
    )


def _add_version(
    session: Session,
    scenario_id: str,
    version: str,
    status: str,
    published_at: datetime,
) -> None:
    session.add(
        ScenarioVersionModel(
            scenario_version_id=f"{scenario_id}-{version}",
            scenario_id=scenario_id,
            version=version,
            status=status,
            objectives=[],
            target_profile={},
            runtime_template={},
            action_policy={},
            resource_budget={},
            verification_contract={},
            published_at=published_at if status == "published" else None,
        )
    )
