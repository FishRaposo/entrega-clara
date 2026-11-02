"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  addCartItem,
  ApiError,
  applyCoupon,
  cancelOrder,
  checkout,
  getCart,
  getMenu,
  getTracking,
  listAddresses,
  listMyOrders,
  listRestaurants,
  rateOrder,
  removeCartItem,
  removeCoupon,
  updateCartItem,
} from "../lib/api-client";
import type {
  Address,
  Cart,
  MenuItem,
  RestaurantSummary,
  TrackingView,
} from "../lib/api-types";
import { deliveryStatusLabel, formatBRL, orderStateLabel } from "../lib/format";
import { DEMO_IDENTITIES } from "../lib/identities";
import { useOrderStream } from "../lib/use-order-stream";
import { DeliveryMap, RouteStopList } from "./delivery-map";

const ID = DEMO_IDENTITIES.customer;

const CUSTOMER_EVENT_LABELS: Record<string, string> = {
  "order.placed": "Pedido recebido",
  "payment.approved": "Pagamento simulado aprovado",
  "payment.declined": "Pagamento simulado recusado",
  "order.confirmed": "Pedido confirmado pelo restaurante",
  "order.preparing": "Pedido em preparo",
  "order.ready": "Pedido pronto para retirada",
  "order.rated": "Avaliação registrada",
  "order.cancelled": "Pedido cancelado",
  "delivery.assigned": "Entregador a caminho do restaurante",
  "delivery.picked_up": "Pedido retirado pelo entregador",
  "delivery.en_route": "Pedido a caminho",
  "delivery.delivered": "Pedido entregue",
  "courier.location_updated": "Posição do entregador atualizada",
  "route.replanned": "Rota recalculada",
  "notification.created": "Notificação enviada",
  "tracking.delayed": "Rastreamento atrasado",
};

const customerEventLabel = (type: string) =>
  CUSTOMER_EVENT_LABELS[type] ?? type.replace(/[._]/g, " ");

function formatEventTime(value: string): string {
  return new Date(value).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function CustomerFlow() {
  const [restaurants, setRestaurants] = useState<RestaurantSummary[]>([]);
  const [selected, setSelected] = useState<RestaurantSummary | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressId, setAddressId] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("pix");
  const [couponCode, setCouponCode] = useState("");
  const [orderId, setOrderId] = useState<string | null>(null);
  const [tracking, setTracking] = useState<TrackingView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [menuLoading, setMenuLoading] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [placingOrder, setPlacingOrder] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [cancelMessage, setCancelMessage] = useState<string | null>(null);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const cancelDialogRef = useRef<HTMLDialogElement>(null);
  const cancelSafeRef = useRef<HTMLButtonElement>(null);
  const cancelMessageRef = useRef<HTMLParagraphElement>(null);
  const stream = useOrderStream(ID, orderId);

  const refreshCart = useCallback(async () => setCart(await getCart(ID)), []);

  useEffect(() => {
    void (async () => {
      try {
        const [restaurantList, addressList, orderList] = await Promise.all([
          listRestaurants(),
          listAddresses(ID),
          listMyOrders(ID),
        ]);
        setRestaurants(restaurantList.restaurants);
        setAddresses(addressList.addresses);
        if (addressList.addresses[0]) setAddressId(addressList.addresses[0].id);
        if (orderList.orders[0]) setOrderId(orderList.orders[0].id);
        await refreshCart();
      } catch {
        setError("Não foi possível carregar o catálogo. Verifique a conexão e tente novamente.");
      } finally {
        setCatalogLoading(false);
      }
    })();
  }, [refreshCart]);

  const openRestaurant = async (restaurant: RestaurantSummary) => {
    setSelected(restaurant);
    setError(null);
    setMenuLoading(true);
    try {
      setMenu((await getMenu(restaurant.id)).items);
    } catch {
      setError("Não foi possível carregar o cardápio. Tente novamente.");
    } finally {
      setMenuLoading(false);
    }
  };

  const run = async (label: string, action: () => Promise<unknown>) => {
    setPending(label);
    setError(null);
    try {
      await action();
      await refreshCart();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "A ação não foi concluída. Tente novamente.");
    } finally {
      setPending(null);
    }
  };

  const placeOrder = async () => {
    setPlacingOrder(true);
    setError(null);
    try {
      const result = await checkout(ID, {
        address_id: addressId,
        payment_method: paymentMethod,
      });
      setCancelled(false);
      setCancelMessage(null);
      setOrderId(result.order_id);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Não foi possível finalizar o pedido. Tente novamente.",
      );
    } finally {
      setPlacingOrder(false);
    }
  };

  useEffect(() => {
    setCancelled(false);
    setCancelMessage(null);
  }, [orderId]);

  useEffect(() => {
    if (cancelMessage) {
      cancelMessageRef.current?.focus();
    }
  }, [cancelMessage]);

  const openCancelDialog = () => {
    setCancelError(null);
    cancelDialogRef.current?.showModal();
    cancelSafeRef.current?.focus();
  };

  const confirmCancel = async () => {
    if (!orderId) {
      return;
    }
    setCancelling(true);
    setCancelError(null);
    try {
      await cancelOrder(ID, orderId);
      setCancelled(true);
      setCancelMessage(
        "Pedido cancelado. Se havia pagamento aprovado, o estorno simulado foi registrado.",
      );
      cancelDialogRef.current?.close();
      try {
        setTracking(await getTracking(ID, orderId));
      } catch {
        // Cancellation is committed; the local state already reflects it.
      }
    } catch (err) {
      setCancelError(
        err instanceof ApiError
          ? err.detail
          : "Não foi possível cancelar o pedido. Tente novamente.",
      );
    } finally {
      setCancelling(false);
    }
  };

  useEffect(() => {
    if (!orderId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const view = await getTracking(ID, orderId);
        if (!cancelled) setTracking(view);
      } catch {
        // tracking not available yet
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), 4000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [orderId]);

  const itemName = (menuItemId: string) =>
    menu.find((m) => m.id === menuItemId)?.name ?? menuItemId;

  if (orderId) {
    const snapshot = stream.snapshot;
    const state = cancelled
      ? "cancelled"
      : tracking?.order_status ?? snapshot?.state ?? "placed";
    const route = tracking?.route ?? snapshot?.route ?? null;
    return (
      <section className="role-page" aria-labelledby="tracking-title">
        <p className="eyebrow">Acompanhamento ao vivo</p>
        <h1 id="tracking-title">Pedido {orderId}</h1>
        <div className="tracking-workspace">
          <div className="tracking-artifact">
            <DeliveryMap route={route} lastKnown={tracking?.last_known_location} />
            {tracking && tracking.positions.length > 0 ? (
              <p className="quiet">{tracking.positions.length} pontos de rastreamento.</p>
            ) : null}
          </div>
          <aside className="tracking-detail panel" aria-labelledby="tracking-detail-title">
            <h2 id="tracking-detail-title">Andamento</h2>
            <p>
              Estado atual: <strong>{orderStateLabel(state)}</strong>
              {tracking?.delivery_status
                ? ` · entrega ${deliveryStatusLabel(tracking.delivery_status)}`
                : ""}
              {stream.connected ? " · transmissão ao vivo" : ""}
            </p>
            {route?.stops.length ? (
              <section className="tracking-stops" aria-label="Paradas da rota">
                <h3>Paradas</h3>
                <RouteStopList stops={route.stops} />
              </section>
            ) : null}
            {error ? <p role="alert">{error}</p> : null}
            {pending ? <p role="status" className="quiet">{pending}</p> : null}
            {cancelMessage ? (
              <p ref={cancelMessageRef} tabIndex={-1} className="notice success">
                {cancelMessage}
              </p>
            ) : null}
            <section className="tracking-events" aria-labelledby="tracking-events-title">
              <h3 id="tracking-events-title">Eventos do pedido</h3>
              {stream.events.length > 0 ? (
                <ol
                  className="event-feed"
                  tabIndex={0}
                  aria-label="Eventos do pedido, região rolável"
                >
                  {stream.events.map((event) => (
                    <li key={event.id}>
                      {event.occurred_at ? (
                        <time dateTime={event.occurred_at}>
                          {formatEventTime(event.occurred_at)}
                        </time>
                      ) : null}{" "}
                      {customerEventLabel(event.type)}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="quiet">Sem eventos ainda. A primeira atualização do pedido aparece aqui.</p>
              )}
            </section>
            {state === "placed" || state === "confirmed" ? (
              <>
                <button type="button" className="danger-button" onClick={openCancelDialog}>
                  Cancelar pedido
                </button>
                <dialog
                  ref={cancelDialogRef}
                  className="cancel-dialog"
                  aria-labelledby="cancel-order-title"
                  aria-describedby="cancel-order-description"
                  onCancel={(event) => {
                    if (cancelling) {
                      event.preventDefault();
                    }
                  }}
                  onClose={() => setCancelError(null)}
                >
                  <h2 id="cancel-order-title">Cancelar pedido?</h2>
                  <p id="cancel-order-description">
                    O pedido {orderId} será cancelado. Se o pagamento simulado foi aprovado, o valor
                    será estornado. Esta ação não pode ser desfeita.
                  </p>
                  {cancelError ? <p role="alert">{cancelError}</p> : null}
                  <div className="dialog-actions">
                    <button
                      ref={cancelSafeRef}
                      type="button"
                      className="secondary-button"
                      disabled={cancelling}
                      onClick={() => cancelDialogRef.current?.close()}
                    >
                      Manter pedido
                    </button>
                    <button
                      type="button"
                      className="danger-button solid"
                      disabled={cancelling}
                      onClick={() => void confirmCancel()}
                    >
                      {cancelling ? "Cancelando pedido…" : "Cancelar pedido"}
                    </button>
                  </div>
                </dialog>
              </>
            ) : null}
            {state === "delivered" ? (
              <section className="tracking-rating" aria-label="Avaliar pedido">
                <h3>Avaliar pedido</h3>
                <div className="demo-actions" role="group" aria-label="Estrelas">
                  {[1, 2, 3, 4, 5].map((stars) => (
                    <button
                      key={stars}
                      type="button"
                      className="secondary-button"
                      disabled={pending !== null}
                      onClick={() =>
                        run("Registrando avaliação…", async () => {
                          await rateOrder(ID, orderId, stars);
                          const view = await getTracking(ID, orderId);
                          setTracking(view);
                        })
                      }
                    >
                      {stars}★
                    </button>
                  ))}
                </div>
              </section>
            ) : null}
            <div className="demo-actions">
              <button
                type="button"
                className="primary-button"
                disabled={pending !== null}
                onClick={() => void refreshCart().then(() => setOrderId(null))}
              >
                Fazer novo pedido
              </button>
            </div>
          </aside>
        </div>
      </section>
    );
  }

  return (
    <section className="role-page" aria-labelledby="customer-title">
      <p className="eyebrow">Cliente</p>
      <h1 id="customer-title">Descubra, monte a sacola e peça.</h1>
      {error ? <p role="alert">{error}</p> : null}
      {catalogLoading ? (
        <p role="status" className="quiet">Carregando catálogo, endereços e pedidos…</p>
      ) : null}
      {pending ? <p role="status" className="quiet">{pending}</p> : null}

      <div className="panel-grid">
        <div className="panel">
          <h2>Restaurantes</h2>
          <ul className="stacked-list">
            {restaurants.map((restaurant) => (
              <li key={restaurant.id}>
                <button
                  type="button"
                  className="link-button"
                  aria-pressed={selected?.id === restaurant.id}
                  onClick={() => void openRestaurant(restaurant)}
                >
                  <strong>{restaurant.name}</strong> · {restaurant.cuisine}
                  <br />
                  <span className="quiet">
                    {restaurant.address_label} · entrega {formatBRL(restaurant.delivery_fee_minor)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        {selected ? (
          <div className="panel">
            <h2>Cardápio de {selected.name}</h2>
            {menuLoading ? (
              <p role="status" className="quiet">Carregando cardápio…</p>
            ) : null}
            <ul className="stacked-list">
              {menu.map((item) => (
                <li key={item.id}>
                  <strong>{item.name}</strong> · {formatBRL(item.price_minor, item.currency)}
                  <br />
                  <span className="quiet">{item.description}</span>
                  <br />
                  <button
                    type="button"
                    disabled={!item.available || pending !== null}
                    onClick={() => void run("Adicionando à sacola…", () => addCartItem(ID, item.id, 1))}
                  >
                    {item.available ? "Adicionar" : "Indisponível"}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {cart && cart.lines.length > 0 ? (
          <div className="panel">
            <h2>Sacola</h2>
            <ul className="stacked-list">
              {cart.lines.map((line) => (
                <li key={line.id}>
                  <strong>{itemName(line.menu_item_id)}</strong> × {line.quantity}
                  <div className="line-controls">
                    <button
                      type="button"
                      aria-label={`Diminuir ${itemName(line.menu_item_id)}`}
                      disabled={pending !== null}
                      onClick={() =>
                        void run("Atualizando a sacola…", () =>
                          line.quantity > 1
                            ? updateCartItem(ID, line.id, { quantity: line.quantity - 1 })
                            : removeCartItem(ID, line.id),
                        )
                      }
                    >
                      −
                    </button>
                    <button
                      type="button"
                      aria-label={`Aumentar ${itemName(line.menu_item_id)}`}
                      disabled={pending !== null}
                      onClick={() =>
                        void run("Atualizando a sacola…", () =>
                          updateCartItem(ID, line.id, { quantity: line.quantity + 1 }),
                        )
                      }
                    >
                      +
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={pending !== null}
                      onClick={() => void run("Removendo item…", () => removeCartItem(ID, line.id))}
                    >
                      Remover
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            <dl className="totals">
              <div>
                <dt>Subtotal</dt>
                <dd>{formatBRL(cart.subtotal_minor)}</dd>
              </div>
              <div>
                <dt>Desconto</dt>
                <dd>−{formatBRL(cart.discount_minor)}</dd>
              </div>
              <div>
                <dt>Entrega</dt>
                <dd>{formatBRL(cart.delivery_fee_minor)}</dd>
              </div>
              <div>
                <dt>Total</dt>
                <dd>
                  <strong>{formatBRL(cart.total_minor)}</strong>
                </dd>
              </div>
            </dl>
            {cart.coupon_code ? (
              <p>
                Cupom <code>{cart.coupon_code}</code>{" "}
                <button
                  type="button"
                  className="secondary-button"
                  disabled={pending !== null}
                  onClick={() => void run("Removendo cupom…", () => removeCoupon(ID))}
                >
                  Remover
                </button>
              </p>
            ) : (
              <p>
                <label htmlFor="coupon-input">Cupom: </label>
                <input
                  id="coupon-input"
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value)}
                  placeholder="BEM-VINDO-DEMO"
                  disabled={pending !== null}
                />{" "}
                <button
                  type="button"
                  disabled={!couponCode.trim() || pending !== null}
                  onClick={() => void run("Aplicando cupom…", () => applyCoupon(ID, couponCode.trim()))}
                >
                  Aplicar
                </button>
              </p>
            )}
            <p>
              <label htmlFor="address-select">Entregar em: </label>
              <select
                id="address-select"
                value={addressId}
                disabled={placingOrder}
                onChange={(e) => setAddressId(e.target.value)}
              >
                {addresses.map((address) => (
                  <option key={address.id} value={address.id}>
                    {address.label} · {address.formatted}
                  </option>
                ))}
              </select>
            </p>
            <p>
              <label htmlFor="payment-select">Pagamento: </label>
              <select
                id="payment-select"
                value={paymentMethod}
                disabled={placingOrder}
                onChange={(e) => setPaymentMethod(e.target.value)}
              >
                <option value="pix">Pix</option>
                <option value="card">Cartão</option>
                <option value="wallet">Carteira digital</option>
              </select>
            </p>
            <button
              type="button"
              className="primary-button"
              disabled={!addressId || placingOrder}
              aria-busy={placingOrder}
              onClick={() => void placeOrder()}
            >
              {placingOrder ? "Finalizando pedido…" : "Finalizar pedido"}
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
