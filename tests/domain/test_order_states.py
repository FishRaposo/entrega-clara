import pytest
from delivery_platform.domain.errors import InvalidOrderTransition
from delivery_platform.domain.order_states import OrderState, transition_order


def test_order_state_values_match_the_delivery_lifecycle_contract():
    assert [state.value for state in OrderState] == [
        "placed",
        "confirmed",
        "preparing",
        "ready_for_pickup",
        "courier_assigned",
        "picked_up",
        "en_route",
        "delivered",
        "rated",
        "cancelled",
    ]


def test_order_can_move_from_preparing_to_ready_for_pickup():
    assert (
        transition_order(OrderState.PREPARING, OrderState.READY_FOR_PICKUP)
        == OrderState.READY_FOR_PICKUP
    )


def test_order_cannot_move_from_placed_to_delivered():
    with pytest.raises(InvalidOrderTransition):
        transition_order(OrderState.PLACED, OrderState.DELIVERED)


@pytest.mark.parametrize(
    ("current", "requested"),
    (
        (OrderState.PLACED, OrderState.CONFIRMED),
        (OrderState.PLACED, OrderState.CANCELLED),
        (OrderState.CONFIRMED, OrderState.PREPARING),
        (OrderState.CONFIRMED, OrderState.CANCELLED),
        (OrderState.PREPARING, OrderState.READY_FOR_PICKUP),
        (OrderState.READY_FOR_PICKUP, OrderState.COURIER_ASSIGNED),
        (OrderState.COURIER_ASSIGNED, OrderState.PICKED_UP),
        (OrderState.PICKED_UP, OrderState.EN_ROUTE),
        (OrderState.EN_ROUTE, OrderState.DELIVERED),
        (OrderState.DELIVERED, OrderState.RATED),
    ),
)
def test_order_allows_each_contract_transition(current: OrderState, requested: OrderState):
    assert transition_order(current, requested) == requested


@pytest.mark.parametrize("terminal_state", (OrderState.RATED, OrderState.CANCELLED))
def test_terminal_order_states_reject_further_transitions(terminal_state: OrderState):
    with pytest.raises(InvalidOrderTransition):
        transition_order(terminal_state, OrderState.PLACED)
