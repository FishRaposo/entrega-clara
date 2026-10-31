"use client";

import { useCallback, useEffect, useState } from "react";

import {
  addCartItem,
  ApiError,
  applyCoupon,
  checkout,
  getCart,
  getMenu,
  getTracking,
  listAddresses,
  listMyOrders,
  listRestaurants,
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
import { DeliveryMap } from "./delivery-map";

const ID = DEMO_IDENTITIES.customer;

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
        setError("Não foi possível carregar o catálogo. A API local está ativa?");
      }
    })();
  }, [refreshCart]);

  const openRestaurant = async (restaurant: RestaurantSummary) => {
    setSelected(restaurant);
    setError(null);
    try {
      setMenu((await getMenu(restaurant.id)).items);
    } catch {
      setError("Não foi possível carregar o cardápio.");
    }
  };

  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
      await refreshCart();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "A ação falhou. Tente novamente.");
    }
  };

  const placeOrder = () =>
    run(async () => {
      const result = await checkout(ID, {
        address_id: addressId,
        payment_method: paymentMethod,
      });
      setOrderId(result.order_id);
    });

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
    const state = tracking?.order_status ?? snapshot?.state ?? "placed";
    return (
      <section className="role-page" aria-labelledby="tracking-title">
        <p className="eyebrow">Acompanhamento ao vivo</p>
        <h1 id="tracking-title">Pedido {orderId}</h1>
        <p>
          Estado atual: <strong>{orderStateLabel(state)}</strong>
          {tracking?.delivery_status
            ? ` · entrega ${deliveryStatusLabel(tracking.delivery_status)}`
            : ""}
          {stream.connected ? " · transmissão ao vivo" : ""}
        </p>
        <DeliveryMap
          route={tracking?.route ?? snapshot?.route ?? null}
          lastKnown={tracking?.last_known_location}
        />
        {tracking && tracking.positions.length > 0 ? (
          <p className="quiet">{tracking.positions.length} pontos de rastreamento.</p>
        ) : null}
        {stream.events.length > 0 ? (
          <ol className="event-feed">
            {stream.events.map((event) => (
              <li key={event.id}>
                <code>{event.type}</code>
              </li>
            ))}
          </ol>
        ) : null}
        <div className="demo-actions">
          <button type="button" className="secondary-button" onClick={() => void refreshCart().then(() => setOrderId(null))}>
            Fazer novo pedido
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="role-page" aria-labelledby="customer-title">
      <p className="eyebrow">Cliente</p>
      <h1 id="customer-title">Descubra, monte a sacola e peça.</h1>
      {error ? <p role="alert">{error}</p> : null}

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
                  <strong>{restaurant.name}</strong> — {restaurant.cuisine}
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
            <h2>Cardápio — {selected.name}</h2>
            <ul className="stacked-list">
              {menu.map((item) => (
                <li key={item.id}>
                  <strong>{item.name}</strong> · {formatBRL(item.price_minor, item.currency)}
                  <br />
                  <span className="quiet">{item.description}</span>
                  <br />
                  <button
                    type="button"
                    disabled={!item.available}
                    onClick={() => void run(() => addCartItem(ID, item.id, 1))}
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
                      onClick={() =>
                        void run(() =>
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
                      onClick={() =>
                        void run(() => updateCartItem(ID, line.id, { quantity: line.quantity + 1 }))
                      }
                    >
                      +
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => void run(() => removeCartItem(ID, line.id))}
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
                <button type="button" className="secondary-button" onClick={() => void run(() => removeCoupon(ID))}>
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
                />{" "}
                <button
                  type="button"
                  disabled={!couponCode.trim()}
                  onClick={() => void run(() => applyCoupon(ID, couponCode.trim()))}
                >
                  Aplicar
                </button>
              </p>
            )}
            <p>
              <label htmlFor="address-select">Entregar em: </label>
              <select id="address-select" value={addressId} onChange={(e) => setAddressId(e.target.value)}>
                {addresses.map((address) => (
                  <option key={address.id} value={address.id}>
                    {address.label} — {address.formatted}
                  </option>
                ))}
              </select>
            </p>
            <p>
              <label htmlFor="payment-select">Pagamento: </label>
              <select
                id="payment-select"
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
              >
                <option value="pix">Pix</option>
                <option value="card">Cartão</option>
                <option value="wallet">Carteira digital</option>
              </select>
            </p>
            <button type="button" className="primary-button" disabled={!addressId} onClick={() => void placeOrder()}>
              Finalizar pedido
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
