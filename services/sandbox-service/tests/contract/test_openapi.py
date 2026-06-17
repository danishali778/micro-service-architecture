from pathlib import Path

import yaml
from openapi_spec_validator import validate


def test_openapi_contract_is_valid(service_root: Path) -> None:
    contract_path = service_root / "contracts" / "openapi" / "openapi.yaml"
    with contract_path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    validate(document)
    assert "/internal/v1/sandboxes" in document["paths"]
    assert "/internal/v1/sandboxes/{sandbox_id}/terminate" in document["paths"]
