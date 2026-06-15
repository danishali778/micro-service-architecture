from pathlib import Path
from typing import Any, cast

import yaml
from app.main import create_app
from conftest import make_test_settings
from openapi_spec_validator import validate

CONTRACT = Path(__file__).parents[2] / "contracts" / "openapi" / "openapi.yaml"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def test_openapi_contract_is_valid() -> None:
    document = cast(dict[str, Any], yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))

    validate(document)


def test_implemented_routes_match_service_owned_contract() -> None:
    contract = cast(dict[str, Any], yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))
    generated = create_app(settings=make_test_settings()).openapi()

    contract_operations = {
        (path, method)
        for path, path_item in cast(dict[str, dict[str, Any]], contract["paths"]).items()
        for method in path_item
        if method in HTTP_METHODS
    }
    generated_operations = {
        (path, method)
        for path, path_item in cast(dict[str, dict[str, Any]], generated["paths"]).items()
        for method in path_item
        if method in HTTP_METHODS
    }

    assert generated_operations == contract_operations
