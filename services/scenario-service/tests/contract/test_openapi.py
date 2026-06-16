from pathlib import Path

from openapi_spec_validator import validate
from yaml import safe_load


def test_openapi_contract_is_valid() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "contracts" / "openapi" / "openapi.yaml"
    document = safe_load(contract_path.read_text(encoding="utf-8"))

    validate(document)


def test_openapi_documents_implemented_routes() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "contracts" / "openapi" / "openapi.yaml"
    document = safe_load(contract_path.read_text(encoding="utf-8"))

    assert "/health/live" in document["paths"]
    assert "/health/ready" in document["paths"]
    assert "/internal/v1/scenarios" in document["paths"]
    assert "/internal/v1/scenario-snapshots" in document["paths"]
