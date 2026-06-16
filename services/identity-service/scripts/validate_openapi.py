from pathlib import Path

from openapi_spec_validator import validate
from yaml import safe_load


def main() -> None:
    contract_path = Path(__file__).resolve().parents[1] / "contracts" / "openapi" / "openapi.yaml"
    with contract_path.open(encoding="utf-8") as handle:
        document = safe_load(handle)
    validate(document)


if __name__ == "__main__":
    main()
