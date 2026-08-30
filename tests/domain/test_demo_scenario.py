import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from delivery_platform.demo.scenario import DemoScenario
from delivery_platform.domain.errors import DemoScenarioError


def test_demo_reset_returns_the_initial_lunch_rush_snapshot():
    scenario = DemoScenario.from_seed_file("data/scenarios/lunch-rush.json")

    snapshot = scenario.reset()

    assert snapshot["scenario_id"] == "lunch-rush"
    assert snapshot["clock_minutes"] == 0
    assert snapshot["active_order"]["state"] == "placed"


def test_demo_advance_is_replayable():
    scenario = DemoScenario.from_seed_file("data/scenarios/lunch-rush.json")

    first = scenario.reset()
    first_after_event = scenario.advance_event()
    scenario.reset()
    second_after_event = scenario.advance_event()

    assert first["scenario_id"] == "lunch-rush"
    assert first_after_event == second_after_event


def test_demo_advance_minutes_changes_only_the_deterministic_clock():
    scenario = DemoScenario.from_seed_file("data/scenarios/lunch-rush.json")

    snapshot = scenario.advance_minutes(12)

    assert snapshot["clock_minutes"] == 12
    assert snapshot["active_order"]["state"] == "placed"


def test_demo_cannot_advance_beyond_seeded_events():
    scenario = DemoScenario.from_seed_file("data/scenarios/lunch-rush.json")

    for _ in range(10):
        scenario.advance_event()

    with pytest.raises(DemoScenarioError, match="No more demo events"):
        scenario.advance_event()


def test_demo_snapshots_and_reset_are_isolated_from_nested_mutations():
    scenario = DemoScenario.from_seed_file("data/scenarios/lunch-rush.json")
    snapshot = scenario.snapshot()

    snapshot["active_order"]["state"] = "delivered"
    snapshot["courier"]["latitude"] = 0

    assert scenario.snapshot()["active_order"]["state"] == "placed"
    assert scenario.reset()["courier"]["latitude"] == 0.001


def test_demo_batch_rolls_back_when_a_later_event_is_invalid():
    seed = json.loads(Path("data/scenarios/lunch-rush.json").read_text(encoding="utf-8"))
    seed["events"][1]["order_state"] = "delivered"
    scenario = DemoScenario.from_seed_data(seed)
    before = scenario.snapshot()

    with pytest.raises(DemoScenarioError, match="cannot be applied"):
        scenario.advance_events(2)

    assert scenario.snapshot() == before
    assert scenario.remaining_event_count == len(seed["events"])


def test_concurrent_demo_batches_are_serialized():
    class InstrumentedScenario(DemoScenario):
        active_applications = 0
        maximum_active_applications = 0
        observation_lock = threading.Lock()

        def _apply_event_to_state(self, state, event):  # type: ignore[no-untyped-def]
            with self.observation_lock:
                self.active_applications += 1
                self.maximum_active_applications = max(
                    self.maximum_active_applications,
                    self.active_applications,
                )
            time.sleep(0.02)
            try:
                super()._apply_event_to_state(state, event)
            finally:
                with self.observation_lock:
                    self.active_applications -= 1

    scenario = InstrumentedScenario.from_seed_file("data/scenarios/lunch-rush.json")

    with ThreadPoolExecutor(max_workers=2) as executor:
        snapshots = list(executor.map(scenario.advance_events, (1, 1)))

    assert len(snapshots) == 2
    assert scenario.maximum_active_applications == 1
    assert scenario.snapshot()["active_order"]["state"] == "preparing"
