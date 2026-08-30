import json
import os
import site
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.data.validate_seed import validate_seed


def write_seed(tmp_path, seed):
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(json.dumps(seed), encoding="utf-8")
    return seed_path


def test_seed_validation_cli_runs_without_pythonpath():
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    dependency_paths = tuple(
        path
        for path in (*site.getsitepackages(), site.getusersitepackages())
        if Path(path).is_dir()
    )
    assert dependency_paths

    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            (
                "import runpy, sys\n"
                "sys.path[0:0] = sys.argv[1:-2]\n"
                "sys.argv = sys.argv[-2:]\n"
                "runpy.run_path(sys.argv[0], run_name='__main__')\n"
            ),
            *dependency_paths,
            "scripts/data/validate_seed.py",
            "data/scenarios/lunch-rush.json",
        ],
        cwd=Path(__file__).parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Seed validation passed: data/scenarios/lunch-rush.json" in result.stdout


def test_lunch_rush_seed_contains_required_demo_entities():
    result = validate_seed("data/scenarios/lunch-rush.json")

    assert result.valid is True
    assert result.missing_entities == ()
    assert result.secret_like_fields == ()


def test_seed_validation_reports_missing_entities_and_secret_like_inputs(tmp_path):
    seed = json.loads(Path("data/scenarios/lunch-rush.json").read_text(encoding="utf-8"))
    del seed["initial_state"]["coupon"]
    seed["initial_state"]["payment"]["api_key"] = "not-a-real-secret"
    seed["initial_state"]["payment"]["reference"] = "sk_live_abc123"
    seed_path = write_seed(tmp_path, seed)

    result = validate_seed(seed_path)

    assert result.valid is False
    assert result.missing_entities == ("coupon",)
    assert result.secret_like_fields == (
        "initial_state.payment.api_key",
        "initial_state.payment.reference",
    )


@pytest.mark.parametrize(
    "mutate",
    (
        lambda seed: seed.update(events=[]),
        lambda seed: seed["events"][0].pop("minutes"),
        lambda seed: seed["events"][0].update(notification=42),
        lambda seed: seed["events"][0].update(courier_update={"status": "teleporting"}),
    ),
)
def test_seed_validation_rejects_malformed_event_schema(tmp_path, mutate):
    seed = json.loads(Path("data/scenarios/lunch-rush.json").read_text(encoding="utf-8"))
    mutate(seed)

    result = validate_seed(write_seed(tmp_path, seed))

    assert result.valid is False
    assert result.schema_errors


def test_seed_validation_dry_runs_the_full_transition_sequence(tmp_path):
    seed = json.loads(Path("data/scenarios/lunch-rush.json").read_text(encoding="utf-8"))
    seed["events"][3]["order_state"] = "delivered"

    result = validate_seed(write_seed(tmp_path, seed))

    assert result.valid is False
    assert result.schema_errors == ()
    assert result.replay_error == "The next demo event cannot be applied."
