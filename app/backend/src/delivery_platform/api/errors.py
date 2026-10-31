"""Exception handlers mapping failures to the stable error envelope."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from delivery_platform.domain.errors import DemoScenarioError, DomainError

ERROR_NAMESPACE = "https://entrega-clara.example/errors"


def _envelope(request: Request, *, status: int, code: str, detail: str,
              field_errors: dict[str, str] | None = None) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "") or "cor_unknown"
    body = {
        "type": f"{ERROR_NAMESPACE}/{code.replace('_', '-')}",
        "title": _title_for(code),
        "status": status,
        "code": code,
        "detail": detail,
        "field_errors": field_errors or {},
        "correlation_id": correlation_id,
    }
    return JSONResponse(status_code=status, content=body)


def _title_for(code: str) -> str:
    return {
        "payment_declined": "Pagamento recusado",
        "coupon_invalid": "Cupom inválido",
        "coupon_expired": "Cupom expirado",
        "invalid_transition": "Transição inválida",
        "role_forbidden": "Ação não permitida",
        "ownership_forbidden": "Recurso de outra identidade",
        "not_found": "Não encontrado",
        "identity_required": "Identidade necessária",
        "idempotency_conflict": "Conflito de idempotência",
        "cart_empty": "Carrinho vazio",
        "item_unavailable": "Item indisponível",
        "restaurant_unavailable": "Restaurante indisponível",
        "courier_unavailable": "Entregador indisponível",
        "route_unavailable": "Rota indisponível",
        "validation_error": "Requisição inválida",
    }.get(code, "Erro")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, error: DomainError) -> JSONResponse:
        return _envelope(
            request, status=error.http_status, code=error.code, detail=error.message
        )

    @app.exception_handler(DemoScenarioError)
    async def demo_error_handler(request: Request, error: DemoScenarioError) -> JSONResponse:
        return _envelope(request, status=409, code="demo_scenario_error", detail=str(error))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        field_errors = {
            ".".join(str(part) for part in err["loc"] if part != "body"): str(err["msg"])
            for err in error.errors()
        }
        return _envelope(
            request,
            status=422,
            code="validation_error",
            detail="A requisição está incompleta ou mal formada.",
            field_errors=field_errors,
        )
