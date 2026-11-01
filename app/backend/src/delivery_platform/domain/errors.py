"""Domain errors mapped to the stable public error envelope.

Every error carries a machine-readable ``code`` and an HTTP status class from the
API contract. Messages are pt-BR, user-facing, and free of internals.
"""


class DomainError(Exception):
    """Base class for domain rejections with a stable public code."""

    code = "domain_error"
    http_status = 422

    def __init__(self, message: str = "A regra de negócio não permite esta operação.") -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "not_found"
    http_status = 404

    def __init__(self, resource: str = "registro") -> None:
        super().__init__(f"O {resource} não foi encontrado.")


class MissingIdentityError(DomainError):
    code = "identity_required"
    http_status = 401

    def __init__(self) -> None:
        super().__init__("A identidade da demonstração é obrigatória ou inválida.")


class RoleForbiddenError(DomainError):
    code = "role_forbidden"
    http_status = 403

    def __init__(self) -> None:
        super().__init__("Este papel não pode executar esta ação.")


class OwnershipForbiddenError(DomainError):
    code = "ownership_forbidden"
    http_status = 403

    def __init__(self) -> None:
        super().__init__("Este recurso pertence a outra identidade.")


class InvalidOrderTransition(DomainError):
    """Raised when an order or delivery is asked to move to an invalid state."""

    code = "invalid_transition"
    http_status = 409

    def __init__(self, message: str = "This order cannot move to the requested state.") -> None:
        super().__init__(message)


class IdempotencyConflictError(DomainError):
    code = "idempotency_conflict"
    http_status = 409

    def __init__(self) -> None:
        super().__init__("Já existe uma requisição diferente com esta chave de idempotência.")


class VersionConflictError(DomainError):
    code = "version_conflict"
    http_status = 409

    def __init__(self) -> None:
        super().__init__("O registro foi alterado por outra operação. Recarregue e tente de novo.")


class PaymentDeclinedError(DomainError):
    code = "payment_declined"

    def __init__(self) -> None:
        super().__init__("O pagamento foi recusado. Tente outro método.")


class CouponInvalidError(DomainError):
    code = "coupon_invalid"

    def __init__(self) -> None:
        super().__init__("O cupom não é válido para este carrinho.")


class CouponExpiredError(DomainError):
    code = "coupon_expired"

    def __init__(self) -> None:
        super().__init__("Este cupom está expirado.")


class CartEmptyError(DomainError):
    code = "cart_empty"

    def __init__(self) -> None:
        super().__init__("O carrinho está vazio.")


class CartRestaurantConflictError(DomainError):
    code = "cart_restaurant_conflict"
    http_status = 409

    def __init__(self) -> None:
        super().__init__("O carrinho já tem itens de outro restaurante. Finalize ou esvazie-o antes.")


class ItemUnavailableError(DomainError):
    code = "item_unavailable"

    def __init__(self) -> None:
        super().__init__("Este item não está disponível no momento.")


class RestaurantUnavailableError(DomainError):
    code = "restaurant_unavailable"

    def __init__(self) -> None:
        super().__init__("Este restaurante não está aceitando pedidos no momento.")


class CourierUnavailableError(DomainError):
    code = "courier_unavailable"
    http_status = 409

    def __init__(self) -> None:
        super().__init__("O entregador não está disponível para esta ação.")


class StaleLocationError(DomainError):
    code = "stale_location"
    http_status = 409

    def __init__(self) -> None:
        super().__init__("Esta posição é mais antiga que a última registrada.")


class RouteUnavailableError(DomainError):
    code = "route_unavailable"
    http_status = 503

    def __init__(self) -> None:
        super().__init__("Não foi possível calcular a rota agora. Tente novamente.")


class BatchInfeasibleError(DomainError):
    """The optimized tour cannot satisfy capacity or the promised windows."""

    code = "batch_infeasible"
    http_status = 409

    def __init__(self, reasons: tuple[str, ...] = ()) -> None:
        if any("capacity" in reason for reason in reasons):
            message = "O lote excede a capacidade do entregador."
        elif any("lateness" in reason or "window" in reason for reason in reasons):
            message = "O lote não cumpre a janela prometida ao cliente."
        else:
            message = "O lote não é viável para este entregador."
        super().__init__(message)


class TrackingDelayedError(DomainError):
    code = "tracking_delayed"
    http_status = 503

    def __init__(self) -> None:
        super().__init__("O rastreamento está temporariamente indisponível.")


class DemoScenarioError(Exception):
    """Raised when a deterministic demo command cannot be applied."""
