from pathlib import Path

import yaml
from openapi_spec_validator import validate


def main() -> None:
    contract_path = Path(__file__).resolve().parents[1] / "contracts" / "openapi" / "openapi.yaml"
    with contract_path.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    validate(document)
    print(f"Validated {contract_path}")


if __name__ == "__main__":
    main()
