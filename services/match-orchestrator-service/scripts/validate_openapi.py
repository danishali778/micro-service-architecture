from pathlib import Path

from openapi_spec_validator import validate
from yaml import safe_load


def main() -> None:
    contract_path = Path(__file__).resolve().parents[1] / "contracts" / "openapi" / "openapi.yaml"
    document = safe_load(contract_path.read_text(encoding="utf-8"))
    validate(document)


if __name__ == "__main__":
    main()
