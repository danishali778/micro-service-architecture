from pathlib import Path
from typing import Any, cast

import yaml
from openapi_spec_validator import validate

CONTRACT = Path(__file__).parents[1] / "contracts" / "openapi" / "openapi.yaml"


def main() -> None:
    document = cast(dict[str, Any], yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))
    validate(document)
    print(f"Validated {CONTRACT}")


if __name__ == "__main__":
    main()
