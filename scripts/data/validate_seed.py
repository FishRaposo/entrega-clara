"""Validate deterministic demo scenario seed files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_INITIAL_STATE_ENTITIES = (
    "customer",
    "restaurant",
    "courier",
    "active_order",
    "coupon",
    "payment",
)
SECRET_LIKE_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?key|auth(?:entication)?[_-]?token|"
    r"credential|password|private[_-]?key|secret|token)",
    re.IGNORECASE,
)
SECRET_LIKE_VALUE = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|"
    r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk_live_[A-Za-z0-9]+|xox[baprs]-[A-Za-z0-9-]+)"
)


@dataclass(frozen=True)
class SeedValidationResult:
    """The deterministic validation outcome for one scenario seed."""

    valid: bool
    missing_entities: tuple[str, ...]
    secret_like_fields: tuple[str, ...]
    schema_errors: tuple[str, ...]
    replay_error: str | None


def _ensure_backend_source_on_path() -> None:
    """Make the application package importable from a source checkout."""
    backend_source = Path(__file__).resolve().parents[2] / "app" / "backend" / "src"
    backend_source_text = str(backend_source)
    if backend_source_text not in sys.path:
        sys.path.insert(0, backend_source_text)


def _validation_error_paths(error: Any) -> tuple[str, ...]:
    return tuple(
        sorted(
            ".".join(str(component) for component in item["loc"])
            for item in error.errors()
        )
    )


def _secret_like_fields(value: Any, path: str = "") -> tuple[str, ...]:
    if isinstance(value, dict):
        fields = {
            f"{path}.{key}" if path else key
            for key in value
            if SECRET_LIKE_KEY.search(key)
        }
        for key, nested_value in value.items():
            nested_path = f"{path}.{key}" if path else key
            fields.update(_secret_like_fields(nested_value, nested_path))
        return tuple(sorted(fields))
    if isinstance(value, list):
        fields: set[str] = set()
        for index, nested_value in enumerate(value):
            fields.update(_secret_like_fields(nested_value, f"{path}[{index}]"))
        return tuple(sorted(fields))
    if isinstance(value, str) and SECRET_LIKE_VALUE.search(value):
        return (path,)
    return ()


def validate_seed(path: str | Path) -> SeedValidationResult:
    """Return deterministic validation findings for a lunch-rush scenario file."""
    _ensure_backend_source_on_path()

    from delivery_platform.demo.models import validate_scenario_seed
    from delivery_platform.demo.scenario import DemoScenario
    from delivery_platform.domain.errors import DemoScenarioError
    from pydantic import ValidationError

    seed_path = Path(path)
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    initial_state = seed.get("initial_state") if isinstance(seed, dict) else None

    missing = []
    if not isinstance(seed, dict) or seed.get("scenario_id") != "lunch-rush":
        missing.append("scenario_id")
    if not isinstance(initial_state, dict):
        missing.append("initial_state")
        initial_state = {}
    elif initial_state.get("scenario_id") != "lunch-rush":
        missing.append("initial_state.scenario_id")

    missing.extend(
        entity
        for entity in REQUIRED_INITIAL_STATE_ENTITIES
        if not isinstance(initial_state.get(entity), dict)
    )
    if not isinstance(seed, dict) or not isinstance(seed.get("events"), list):
        missing.append("events")

    missing_entities = tuple(sorted(missing))
    secret_like_fields = _secret_like_fields(seed)
    schema_errors: tuple[str, ...] = ()
    replay_error: str | None = None
    try:
        validated_seed = validate_scenario_seed(seed)
    except ValidationError as error:
        schema_errors = _validation_error_paths(error)
    else:
        try:
            scenario = DemoScenario(validated_seed)
            scenario.advance_events(len(validated_seed.events))
        except DemoScenarioError as error:
            replay_error = str(error)
    return SeedValidationResult(
        valid=(
            not missing_entities
            and not secret_like_fields
            and not schema_errors
            and replay_error is None
        ),
        missing_entities=missing_entities,
        secret_like_fields=secret_like_fields,
        schema_errors=schema_errors,
        replay_error=replay_error,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a deterministic demo seed.")
    parser.add_argument("path", type=Path, help="Path to the scenario JSON file.")
    args = parser.parse_args()
    result = validate_seed(args.path)
    if result.valid:
        print(f"Seed validation passed: {args.path}")
        return 0

    if result.missing_entities:
        print("Missing required entities: " + ", ".join(result.missing_entities))
    if result.secret_like_fields:
        print("Secret-like fields: " + ", ".join(result.secret_like_fields))
    if result.schema_errors:
        print("Schema errors: " + ", ".join(result.schema_errors))
    if result.replay_error:
        print("Replay error: " + result.replay_error)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
