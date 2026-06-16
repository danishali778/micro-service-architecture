from pathlib import Path

from openapi_spec_validator import validate
from yaml import safe_load


def test_openapi_contract_is_valid() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "contracts" / "openapi" / "openapi.yaml"
    with contract_path.open(encoding="utf-8") as handle:
        document = safe_load(handle)

    validate(document)
