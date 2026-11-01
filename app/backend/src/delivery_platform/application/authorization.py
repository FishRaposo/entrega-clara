"""Authorization checks against an IdentityContext and resource scope."""

from delivery_platform.application.identity import IdentityContext
from delivery_platform.domain.entities import Role
from delivery_platform.domain.errors import OwnershipForbiddenError, RoleForbiddenError


def require_role(identity: IdentityContext, *roles: Role) -> None:
    if identity.role not in roles:
        raise RoleForbiddenError()


def require_same_customer(identity: IdentityContext, customer_id: str) -> None:
    require_role(identity, "customer")
    if identity.identity_id != customer_id:
        raise OwnershipForbiddenError()


def require_restaurant_operator(identity: IdentityContext, restaurant_id: str) -> None:
    require_role(identity, "restaurant")
    if identity.restaurant_id != restaurant_id:
        raise OwnershipForbiddenError()


def require_courier(identity: IdentityContext, courier_id: str) -> None:
    require_role(identity, "courier")
    if identity.courier_id != courier_id:
        raise OwnershipForbiddenError()


def require_operations(identity: IdentityContext) -> None:
    require_role(identity, "operations")


def can_read_order(
    identity: IdentityContext,
    *,
    customer_id: str,
    restaurant_id: str,
    courier_id: str | None = None,
) -> bool:
    """Who may read an order: its customer, its restaurant, its courier, operations.

    ``courier_id`` is the courier currently assigned to the order's delivery (or
    ``None`` while no delivery is assigned). The rule exists because the courier
    console renders the map for the delivery it is running; it must not leak
    orders the courier is not carrying.
    """
    if identity.role == "customer":
        return identity.identity_id == customer_id
    if identity.role == "restaurant":
        return identity.restaurant_id == restaurant_id
    if identity.role == "courier":
        return courier_id is not None and identity.courier_id == courier_id
    return identity.role == "operations"
