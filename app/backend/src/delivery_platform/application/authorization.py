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


def can_read_order(identity: IdentityContext, *, customer_id: str, restaurant_id: str) -> bool:
    """Who may read an order: its customer, its restaurant operator, operations."""
    if identity.role == "customer":
        return identity.identity_id == customer_id
    if identity.role == "restaurant":
        return identity.restaurant_id == restaurant_id
    return identity.role == "operations"
