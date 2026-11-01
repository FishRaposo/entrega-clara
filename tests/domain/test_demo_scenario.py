"""Scenario runner tests: command-script replay through real handlers."""

import uuid
from pathlib import Path

import pytest
from delivery_platform.adapters.seed.loader import load_reference_seed_file
from delivery_platform.application.commands.cart import CartCommands
from delivery_platform.application.commands.checkout import CheckoutCommands
from delivery_platform.application.container import AppContainer, build_container
from delivery_platform.application.context import CommandContext
from delivery_platform.application.identity import IdentityContext
from delivery_platform.core.config import Settings
from delivery_platform.demo.models import validate_scenario_seed
from delivery_platform.demo.runner import ScenarioRunner
from delivery_platform.domain.errors import DemoScenarioError
from delivery_platform.domain.order_states import OrderState

SCENARIO_PATH = Path("data/scenarios/lunch-rush.json")
SEED_PATH = Path("data/seed/brazil.json")


def _container() -> AppContainer:
    container = build_container(Settings())
    load_reference_seed_file(container.store, SEED_PATH)
    return container


def _runner(container: AppContainer) -> ScenarioRunner:
    return ScenarioRunner.from_seed_file(container, SCENARIO_PATH)


def _customer_ctx() -> CommandContext:
    return CommandContext(
        identity=IdentityContext(identity_id="demo-customer", role="customer"),
        correlation_id="cor-test",
        command_id="cmd-test",
        idempotency_key=f"key-{uuid.uuid4().hex[:8]}",
    )


def test_full_script_replay_produces_a_real_rated_order():
    container = _container()
    runner = _runner(container)

    snapshot = runner.advance_events(runner.remaining_event_count)

    assert snapshot["order"]["state"] == "rated"
    assert snapshot["delivery"]["status"] == "delivered"
    assert snapshot["route"]["graph_id"] == "sao-paulo-centro-osm"
    assert snapshot["tracking_points"] >= 2
    assert snapshot["remaining_steps"] == 0

    order_id = snapshot["order"]["id"]
    with container.uow() as uow:
        order = uow.orders.get(order_id)
        assert order.scenario_id == "lunch-rush"
        delivery = uow.deliveries.find_by_order(order_id)
        assert delivery is not None and delivery.scenario_id == "lunch-rush"
        route = uow.route_plans.find_by_delivery(delivery.id)
        assert route is not None and route.scenario_id == "lunch-rush"
        events = uow.event_log.list_for_aggregate(order_id)
        assert {e.type for e in events} >= {
            "order.placed",
            "payment.approved",
            "order.confirmed",
            "order.preparing",
            "order.ready",
        }
        uow.rollback()


def test_scenario_reset_removes_only_scenario_records():
    container = _container()
    runner = _runner(container)
    scenario_order_id = runner.advance_events(runner.remaining_event_count)["order"]["id"]

    # A dynamic order created outside the scenario must survive the reset.
    ctx = _customer_ctx()
    CartCommands(container).add_item(ctx, menu_item_id="menu-sm-01", quantity=1)
    dynamic = CheckoutCommands(container).checkout(
        ctx, address_id="addr-casa", payment_method="pix"
    )

    runner.reset()

    with container.uow() as uow:
        assert uow.orders.find(scenario_order_id) is None
        assert uow.orders.find(dynamic.order.id) is not None
        assert all(
            order.scenario_id != "lunch-rush"
            for order in uow.orders.list_by_state(OrderState.DELIVERED)
        )
        uow.rollback()
    assert runner.remaining_event_count > 0


def test_runner_rejects_advancing_past_the_end():
    container = _container()
    runner = _runner(container)
    runner.advance_events(runner.remaining_event_count)

    with pytest.raises(DemoScenarioError, match="No more demo events"):
        runner.advance_events(1)


def test_runner_wraps_step_failures_in_demo_error():
    container = _container()
    script = validate_scenario_seed(
        {
            "scenario_id": "lunch-rush",
            "description": "broken",
            "steps": [
                {
                    "id": "bad-step",
                    "actor": "demo-customer",
                    "action": "checkout",
                    "params": {"order_id": "$missing_var"},
                }
            ],
        }
    )
    broken = ScenarioRunner(container, script)
    with pytest.raises(DemoScenarioError, match="Variável de cenário ausente"):
        broken.advance_events(1)


def test_reset_is_replayable_across_runs():
    container = _container()
    runner = _runner(container)
    for _ in range(2):
        runner.advance_events(runner.remaining_event_count)
        runner.reset()
    runner.advance_events(runner.remaining_event_count)
    assert runner.snapshot()["order"]["state"] == "rated"
