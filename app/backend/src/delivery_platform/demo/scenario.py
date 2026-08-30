import copy
import json
from pathlib import Path
from threading import RLock
from typing import Any, cast

from pydantic import ValidationError

from delivery_platform.demo.models import ScenarioEvent, ScenarioSeed, validate_scenario_seed
from delivery_platform.domain.errors import DemoScenarioError, InvalidOrderTransition
from delivery_platform.domain.order_states import OrderState, transition_order


class DemoScenario:
    """Replay a fictional demo scenario through serialized atomic commands."""

    def __init__(self, seed: ScenarioSeed) -> None:
        seed_data = seed.model_dump(mode="json")
        self._initial_state = copy.deepcopy(seed_data["initial_state"])
        self._events = tuple(seed.events)
        self._state: dict[str, Any] = {}
        self._event_index = 0
        self._lock = RLock()
        self.reset()

    @classmethod
    def from_seed_data(cls, value: object) -> "DemoScenario":
        """Build a scenario from a fully validated in-memory seed value."""
        try:
            return cls(validate_scenario_seed(value))
        except (TypeError, ValueError, ValidationError) as error:
            raise DemoScenarioError("The demo scenario is unavailable.") from error

    @classmethod
    def from_seed_file(cls, path: str | Path) -> "DemoScenario":
        try:
            loaded: object = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise DemoScenarioError("The demo scenario is unavailable.") from error
        return cls.from_seed_data(loaded)

    def reset(self) -> dict[str, Any]:
        """Restore an independent copy of the initial deterministic state."""
        with self._lock:
            self._state = copy.deepcopy(self._initial_state)
            self._event_index = 0
            return self._snapshot_unlocked()

    def advance_event(self) -> dict[str, Any]:
        """Apply exactly one seed-defined event without consulting wall-clock time."""
        return self.advance_events(1)

    def advance_events(self, event_count: int) -> dict[str, Any]:
        """Validate a complete event batch and commit it as one serialized mutation."""
        if not isinstance(event_count, int) or isinstance(event_count, bool) or event_count < 1:
            raise DemoScenarioError("Event count must be a positive whole number.")

        with self._lock:
            if event_count > self._remaining_event_count_unlocked():
                raise DemoScenarioError("No more demo events are available.")

            candidate_state = copy.deepcopy(self._state)
            candidate_index = self._event_index
            try:
                for event in self._events[candidate_index : candidate_index + event_count]:
                    self._apply_event_to_state(candidate_state, event)
                    candidate_index += 1
            except (KeyError, TypeError, ValueError, InvalidOrderTransition) as error:
                raise DemoScenarioError("The next demo event cannot be applied.") from error

            self._state = candidate_state
            self._event_index = candidate_index
            return self._snapshot_unlocked()

    def advance_minutes(self, minutes: int) -> dict[str, Any]:
        """Advance only the simulated scenario clock."""
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 0:
            raise DemoScenarioError("Minutes must be a non-negative whole number.")
        with self._lock:
            candidate_state = copy.deepcopy(self._state)
            candidate_state["clock_minutes"] = self._clock_minutes(candidate_state) + minutes
            self._state = candidate_state
            return self._snapshot_unlocked()

    def snapshot(self) -> dict[str, Any]:
        """Return an isolated JSON-compatible view of the current state."""
        with self._lock:
            return self._snapshot_unlocked()

    @property
    def remaining_event_count(self) -> int:
        """Return how many seed events can still be applied."""
        with self._lock:
            return self._remaining_event_count_unlocked()

    def _apply_event_to_state(self, state: dict[str, Any], event: ScenarioEvent) -> None:
        order = cast(dict[str, Any], state["active_order"])
        courier = cast(dict[str, Any], state["courier"])
        notifications = cast(list[str], state["notifications"])
        next_clock = self._clock_minutes(state) + event.minutes
        next_order_state: str | None = None

        if event.order_state is not None:
            next_order_state = transition_order(OrderState(order["state"]), event.order_state).value
        courier_update = (
            event.courier_update.model_dump(exclude_none=True)
            if event.courier_update is not None
            else None
        )

        state["clock_minutes"] = next_clock
        if next_order_state is not None:
            order["state"] = next_order_state
        if courier_update is not None:
            courier.update(courier_update)
        if event.notification is not None:
            notifications.append(event.notification)

    def _snapshot_unlocked(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def _remaining_event_count_unlocked(self) -> int:
        return len(self._events) - self._event_index

    @staticmethod
    def _clock_minutes(state: dict[str, Any]) -> int:
        return cast(int, state["clock_minutes"])
