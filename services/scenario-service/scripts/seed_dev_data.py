from datetime import UTC, datetime

from app.core.config import get_settings
from app.infrastructure.database.connection import create_database_engine, create_session_factory
from app.infrastructure.database.models import ScenarioModel, ScenarioVersionModel


def main() -> None:
    settings = get_settings()
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)

    with session_factory() as session:
        session.merge(
            ScenarioModel(
                scenario_id="scn_sql_injection_login",
                slug="sql-injection-login",
                title="SQL Injection Login Bypass",
                summary="Find and exploit an injectable login form.",
                description="A vulnerable login endpoint accepts unsafe SQL input.",
                category="web-security",
                difficulty="beginner",
                tags=["sql-injection", "authentication"],
                visibility="public",
                owner_tenant_id=None,
                estimated_duration_minutes=30,
                created_at=now,
                updated_at=now,
            )
        )
        session.merge(
            ScenarioVersionModel(
                scenario_version_id="scnv_sql_injection_login_1_0_0",
                scenario_id="scn_sql_injection_login",
                version="1.0.0",
                status="published",
                objectives=["Identify the injectable input", "Bypass authentication"],
                target_profile={"runtime": "container", "template_ref": "local/sql-login"},
                runtime_template={"kind": "compose", "ref": "local/sql-login/docker-compose.yml"},
                action_policy={"network": "sandbox-only", "filesystem": "workspace-only"},
                resource_budget={"cpu_limit": "1", "memory_mb": 512, "timeout_seconds": 1800},
                verification_contract={"ref": "verify/sql-login/1.0.0"},
                created_at=now,
                published_at=now,
            )
        )
        session.merge(
            ScenarioModel(
                scenario_id="scn_auth_boundary",
                slug="authorization-boundary",
                title="Authorization Boundary",
                summary="Practice detecting and fixing an authorization bypass.",
                description="A target API exposes tenant data without enforcing ownership.",
                category="web-security",
                difficulty="intermediate",
                tags=["authorization", "multi-tenant"],
                visibility="public",
                owner_tenant_id=None,
                estimated_duration_minutes=45,
                created_at=now,
                updated_at=now,
            )
        )
        session.merge(
            ScenarioVersionModel(
                scenario_version_id="scnv_auth_boundary_1_0_0",
                scenario_id="scn_auth_boundary",
                version="1.0.0",
                status="published",
                objectives=["Find the broken access check", "Propose a safe fix"],
                target_profile={"runtime": "container", "template_ref": "local/auth-boundary"},
                runtime_template={
                    "kind": "compose",
                    "ref": "local/auth-boundary/docker-compose.yml",
                },
                action_policy={"network": "sandbox-only", "filesystem": "workspace-only"},
                resource_budget={"cpu_limit": "1", "memory_mb": 768, "timeout_seconds": 2700},
                verification_contract={"ref": "verify/auth-boundary/1.0.0"},
                created_at=now,
                published_at=now,
            )
        )
        session.commit()

    engine.dispose()
    print("Seeded scenario-service development data.")


if __name__ == "__main__":
    main()
