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


def test_seed_validation_reports_missing_actions_and_secret_like_inputs(tmp_path):
    seed = json.loads(Path("data/scenarios/lunch-rush.json").read_text(encoding="utf-8"))
    seed["steps"] = [s for s in seed["steps"] if s["action"] != "checkout"]
    seed["steps"][0]["params"]["api_key"] = "not-a-real-secret"
    seed["steps"][0]["params"]["reference"] = "sk_live_abc123"
    seed_path = write_seed(tmp_path, seed)

    result = validate_seed(seed_path)

    assert result.valid is False
    assert result.missing_entities == ("checkout",)
    assert result.secret_like_fields == (
        "steps[0].params.api_key",
        "steps[0].params.reference",
    )


@pytest.mark.parametrize(
    "mutate",
    (
        lambda seed: seed.update(steps=[]),
        lambda seed: seed["steps"][0].pop("action"),
        lambda seed: seed["steps"][0].update(action="teleport.order"),
        lambda seed: seed["steps"][0].update(id=""),
    ),
)
def test_seed_validation_rejects_malformed_step_schema(tmp_path, mutate):
    seed = json.loads(Path("data/scenarios/lunch-rush.json").read_text(encoding="utf-8"))
    mutate(seed)

    result = validate_seed(write_seed(tmp_path, seed))

    assert result.valid is False
    assert result.schema_errors


def test_seed_validation_dry_runs_the_full_command_sequence(tmp_path):
    seed = json.loads(Path("data/scenarios/lunch-rush.json").read_text(encoding="utf-8"))
    # Reordering prepare before confirm breaks the real transition contract.
    steps = seed["steps"]
    confirm_idx = next(i for i, s in enumerate(steps) if s["action"] == "restaurant.confirm")
    prepare_idx = next(i for i, s in enumerate(steps) if s["action"] == "restaurant.prepare")
    steps[confirm_idx], steps[prepare_idx] = steps[prepare_idx], steps[confirm_idx]

    result = validate_seed(write_seed(tmp_path, seed))

    assert result.valid is False
    assert result.schema_errors == ()
    assert result.replay_error is not None
    assert "falhou" in result.replay_error
