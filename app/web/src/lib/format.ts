export function formatBRL(minorUnits: number, currency = "BRL"): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
  }).format(minorUnits / 100);
}

export const ORDER_STATE_LABELS: Record<string, string> = {
  placed: "pedido feito",
  confirmed: "confirmado",
  preparing: "em preparo",
  ready_for_pickup: "pronto para retirada",
  courier_assigned: "entregador atribuído",
  picked_up: "retirado",
  en_route: "a caminho",
  delivered: "entregue",
  rated: "avaliado",
  cancelled: "cancelado",
};

export const DELIVERY_STATUS_LABELS: Record<string, string> = {
  offered: "oferta aberta",
  assigned: "atribuída",
  picked_up: "retirada",
  en_route: "em rota",
  delivered: "entregue",
};

export function orderStateLabel(state: string): string {
  return ORDER_STATE_LABELS[state] ?? state;
}

export function deliveryStatusLabel(status: string): string {
  return DELIVERY_STATUS_LABELS[status] ?? status;
}

/** Travel seconds as "4 min 12 s" (or "48 s" below a minute). */
export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(total / 60);
  if (minutes === 0) {
    return `${total} s`;
  }
  return `${minutes} min ${total % 60} s`;
}
