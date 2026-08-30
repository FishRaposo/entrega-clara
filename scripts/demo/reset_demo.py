"""Reset the running local API scenario or preview its offline seed."""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_SCENARIO_PATH = Path(__file__).resolve().parents[2] / "data/scenarios/lunch-rush.json"
DEFAULT_API_URL = "http://localhost:8000"


class DemoResetError(Exception):
    """Report a safe command-line failure while resetting the local demo."""


def preview_seed(path: Path = DEFAULT_SCENARIO_PATH) -> dict[str, Any]:
    """Return a fresh initial-state copy without contacting or mutating the API."""
    scenario = json.loads(path.read_text(encoding="utf-8"))
    return copy.deepcopy(scenario["initial_state"])


def reset_demo(api_url: str = DEFAULT_API_URL) -> dict[str, Any]:
    """Reset the running API scenario and return its new snapshot."""
    endpoint = f"{api_url.rstrip('/')}/api/v1/demo/reset"
    request = Request(endpoint, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            payload: object = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise DemoResetError(
            "The local demo API could not be reset. Start it with 'make dev' or use "
            "'make demo-preview'."
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("scenario_id"), str):
        raise DemoResetError("The local demo API returned an invalid reset response.")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset or preview the deterministic demo.")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("DEMO_API_URL", DEFAULT_API_URL),
        help="Base URL of the running local API.",
    )
    parser.add_argument(
        "--seed-preview",
        action="store_true",
        help="Read and print the offline seed state without resetting the API.",
    )
    parser.add_argument(
        "--seed-path",
        type=Path,
        default=DEFAULT_SCENARIO_PATH,
        help="Seed path used only with --seed-preview.",
    )
    args = parser.parse_args(argv)
    try:
        if args.seed_preview:
            state = preview_seed(args.seed_path)
            print(f"Seed preview available: {state['scenario_id']}")
        else:
            state = reset_demo(args.api_url)
            print(f"Running demo reset: {state['scenario_id']}")
    except (DemoResetError, OSError, KeyError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
