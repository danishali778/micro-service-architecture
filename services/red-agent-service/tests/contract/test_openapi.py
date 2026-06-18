from pathlib import Path

import yaml
from openapi_spec_validator import validate


def test_openapi_contract_is_valid() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "contracts" / "openapi" / "openapi.yaml"

    with contract_path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    validate(document)
