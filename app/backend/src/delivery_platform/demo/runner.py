"""Command-script scenario runner.

Replays the lunch-rush script through the real application command handlers —
the same code path the interactive role surfaces use. Steps tag produced
records with the scenario id so scoped reset removes only scenario-owned data.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError

from delivery_platform.application.commands.cart import CartCommands
from delivery_platform.application.commands.checkout import CheckoutCommands
from delivery_platform.application.commands.courier import CourierCommands
from delivery_platform.application.commands.restaurant import RestaurantCommands
from delivery_platform.application.context import CommandContext
from delivery_platform.demo.models import ScenarioScript, ScenarioStep, validate_scenario_seed
from delivery_platform.domain.entities import PaymentMethod
from delivery_platform.domain.errors import DemoScenarioError, DomainError

if TYPE_CHECKING:
    from delivery_platform.application.container import AppContainer


class ScenarioRunner:
    """Serializes script steps through real commands under one lock."""

    def __init__(self, container: AppContainer, script: ScenarioScript) -> None:
        self._container = container
        self._script = script
        self._step_index = 0
        self._run_id = 0
        self._vars: dict[str, str] = {}
        self._lock = RLock()

    @classmethod
    def from_seed_file(cls, container: AppContainer, path: str | Path) -> ScenarioRunner:
        try:
            loaded: object = json.loads(Path(path).read_text(encoding="utf-8"))
            script = validate_scenario_seed(loaded)
        except (OSError, TypeError, ValueError, ValidationError) as error:
            raise DemoScenarioError("The demo scenario is unavailable.") from error
        return cls(container, script)

    @property
    def scenario_id(self) -> str:
        return self._script.scenario_id

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_unlocked()

    def reset(self) -> dict[str, Any]:
        """Scoped reset: remove scenario records, keep dynamic user data."""
        with self._lock:
            with self._container.uow() as uow:
                uow.scenarios.remove_scenario_records(self._script.scenario_id)
                uow.commit()
            self._step_index = 0
            self._vars = {}
            self._run_id += 1
            return self._snapshot_unlocked()

    def advance_events(self, step_count: int) -> dict[str, Any]:
        if not isinstance(step_count, int) or isinstance(step_count, bool) or step_count < 1:
            raise DemoScenarioError("Event count must be a positive whole number.")
        with self._lock:
            if step_count > self._remaining_unlocked():
                raise DemoScenarioError("No more demo events are available.")
            for _ in range(step_count):
                step = self._script.steps[self._step_index]
                self._execute_step(step)
                self._step_index += 1
            return self._snapshot_unlocked()

    def advance_minutes(self, minutes: int) -> dict[str, Any]:
        if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 0:
            raise DemoScenarioError("Minutes must be a non-negative whole number.")
        with self._lock:
            self._container.clock.advance_minutes(minutes)
            return self._snapshot_unlocked()

    @property
    def remaining_event_count(self) -> int:
        with self._lock:
            return self._remaining_unlocked()

    # --- internals ---

    def _remaining_unlocked(self) -> int:
        return len(self._script.steps) - self._step_index

    def _ctx(self, step: ScenarioStep) -> CommandContext:
        identity = self._container.resolve_identity(step.actor)
        return CommandContext(
            identity=identity,
            correlation_id=f"cor-{self._script.scenario_id}-{self._run_id}-{step.id}",
            command_id=f"cmd-{self._script.scenario_id}-{self._run_id}-{step.id}",
            idempotency_key=f"{self._script.scenario_id}-{self._run_id}-{step.id}-{uuid.uuid4().hex[:6]}",
            scenario_id=self._script.scenario_id,
        )

    def _resolve_params(self, params: dict[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                var_name = value[1:]
                if var_name not in self._vars:
                    raise DemoScenarioError(f"Variável de cenário ausente: {value}.")
                resolved[key] = self._vars[var_name]
            else:
                resolved[key] = value
        return resolved

    def _execute_step(self, step: ScenarioStep) -> None:
        params = self._resolve_params(step.params)
        try:
            if step.action == "clock.advance":
                minutes = int(params.get("minutes", 1))
                self._container.clock.advance_minutes(minutes)
                return
            ctx = self._ctx(step)
            if step.action == "cart.add_item":
                CartCommands(self._container).add_item(
                    ctx,
                    menu_item_id=str(params["menu_item_id"]),
                    quantity=int(params.get("quantity", 1)),
                    observation=str(params.get("observation", "")),
                )
            elif step.action == "cart.apply_coupon":
                CartCommands(self._container).apply_coupon(ctx, code=str(params["code"]))
            elif step.action == "checkout":
                result = CheckoutCommands(self._container).checkout(
                    ctx,
                    address_id=str(params["address_id"]),
                    payment_method=cast(PaymentMethod, str(params["payment_method"])),
                    simulate_outcome=params.get("simulate_outcome"),
                )
                self._vars["order_id"] = result.order.id
            elif step.action == "restaurant.confirm":
                RestaurantCommands(self._container).confirm(ctx, str(params["order_id"]))
            elif step.action == "restaurant.prepare":
                RestaurantCommands(self._container).prepare(ctx, str(params["order_id"]))
            elif step.action == "restaurant.ready":
                order = RestaurantCommands(self._container).ready(ctx, str(params["order_id"]))
                with self._container.uow() as uow:
                    delivery = uow.deliveries.find_by_order(order.id)
                    uow.rollback()
                if delivery is not None:
                    self._vars["delivery_id"] = delivery.id
            elif step.action == "courier.accept":
                CourierCommands(self._container).accept(ctx, str(params["delivery_id"]))
            elif step.action == "courier.pickup":
                CourierCommands(self._container).pickup(ctx, str(params["delivery_id"]))
            elif step.action == "courier.start":
                CourierCommands(self._container).start_route(ctx, str(params["delivery_id"]))
            elif step.action == "courier.location":
                CourierCommands(self._container).update_location(
                    ctx,
                    delivery_id=str(params["delivery_id"]),
                    sequence=int(params["sequence"]),
                    latitude=float(params["latitude"]),
                    longitude=float(params["longitude"]),
                )
            elif step.action == "courier.complete":
                CourierCommands(self._container).complete(ctx, str(params["delivery_id"]))
            else:  # pragma: no cover - schema forbids unknown actions
                raise DemoScenarioError(f"Ação de cenário desconhecida: {step.action}")
        except DomainError as error:
            raise DemoScenarioError(
                f"O passo '{step.id}' falhou: {error.message}"
            ) from error

    def _snapshot_unlocked(self) -> dict[str, Any]:
        with self._container.uow() as uow:
            order_id = self._vars.get("order_id")
            delivery_id = self._vars.get("delivery_id")
            order = uow.orders.find(order_id) if order_id else None
            delivery = uow.deliveries.find(delivery_id) if delivery_id else None
            route = (
                uow.route_plans.find_by_delivery(delivery.id) if delivery else None
            )
            tracking = (
                uow.tracking_events.list_by_delivery(delivery.id) if delivery else []
            )
            notifications = (
                uow.notifications.list_by_order(order_id) if order_id else []
            )
            uow.rollback()
        return {
            "scenario_id": self._script.scenario_id,
            "description": self._script.description,
            "clock": self._container.clock.now().isoformat(),
            "run_id": self._run_id,
            "step_index": self._step_index,
            "steps_total": len(self._script.steps),
            "remaining_steps": self._remaining_unlocked(),
            "order": (
                {"id": order.id, "state": order.state.value, "total_minor": order.total_minor}
                if order
                else None
            ),
            "delivery": (
                {"id": delivery.id, "status": delivery.status, "courier_id": delivery.courier_id}
                if delivery
                else None
            ),
            "route": (
                {
                    "id": route.id,
                    "graph_id": route.graph_id,
                    "distance_meters": route.distance_meters,
                    "estimated_seconds": route.estimated_seconds,
                }
                if route
                else None
            ),
            "tracking_points": len(tracking),
            "notifications": [n.message for n in notifications],
        }
