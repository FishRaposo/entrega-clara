from enum import StrEnum

from delivery_platform.domain.errors import InvalidOrderTransition


class OrderState(StrEnum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    COURIER_ASSIGNED = "courier_assigned"
    PICKED_UP = "picked_up"
    EN_ROUTE = "en_route"
    DELIVERED = "delivered"
    RATED = "rated"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.PLACED: {OrderState.CONFIRMED, OrderState.CANCELLED},
    OrderState.CONFIRMED: {OrderState.PREPARING, OrderState.CANCELLED},
    OrderState.PREPARING: {OrderState.READY_FOR_PICKUP},
    OrderState.READY_FOR_PICKUP: {OrderState.COURIER_ASSIGNED},
    OrderState.COURIER_ASSIGNED: {OrderState.PICKED_UP},
    OrderState.PICKED_UP: {OrderState.EN_ROUTE},
    OrderState.EN_ROUTE: {OrderState.DELIVERED},
    OrderState.DELIVERED: {OrderState.RATED},
    OrderState.RATED: set(),
    OrderState.CANCELLED: set(),
}


def transition_order(current: OrderState, requested: OrderState) -> OrderState:
    """Validate and return an allowed next order state."""
    if requested not in VALID_TRANSITIONS[current]:
        raise InvalidOrderTransition("This order cannot move to the requested state.")
    return requested
