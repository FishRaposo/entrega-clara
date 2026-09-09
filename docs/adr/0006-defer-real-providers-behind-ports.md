# ADR 0006: Simulate external providers before integrating them

## Status

Accepted for Milestone 1; provider selection deferred.

## Context

Payments, identity, maps, geocoding, and notifications are important future capabilities, but each introduces credentials, network failure, provider-specific state, legal terms, billing, privacy concerns, and external test-environment dependencies. Adding them before the shared order loop exists would make the demo fragile and obscure the domain design.

The portfolio still needs to show that the architecture can support real providers later. A boolean payment stub or a client-only role switcher would not demonstrate that boundary well enough.

## Decision

M1 implements deterministic local adapters behind provider-neutral ports:

- `PaymentGateway`: approved, declined, processing-capable outcomes, idempotency, and safe references;
- `IdentityResolver`: seeded demo identities with role and ownership scope;
- `MapRenderer`: MapLibre/MapTiler adapter with a no-provider fallback;
- `Geocoder`: seeded-address implementation only;
- `NotificationSender`: in-app notification projection;
- `EventPublisher`: post-commit in-process hub;
- `Clock`: deterministic scenario clock.

Real providers are evaluated and integrated one at a time in later milestones. Mercado Pago is a Brazil/PIX candidate; Stripe is an international payment candidate; an OIDC provider is the future identity direction. None is selected by this ADR.

## Consequences

### Positive

- The M1 demo is offline-capable and deterministic.
- Provider failure cannot prevent the primary product story.
- Internal state remains stable if a vendor changes SDKs or statuses.
- Tests can cover approved, declined, delayed, duplicate, and unavailable states without real credentials.
- Future provider work has a clear checklist: secrets, signatures, idempotency, retries, reconciliation, quotas, legal terms, and degraded UI.

### Costs and risks

- Simulators can be less realistic than real sandbox behavior.
- A provider-neutral model may need extension when a real payment/auth flow is selected.
- Some portfolio readers may expect a real integration; the README must state what is simulated.

## Non-negotiable provider rules

- Provider SDKs stay in adapters.
- Browser redirects do not prove payment success; verified server/webhook state does.
- Webhooks are signature-checked and deduplicated.
- Provider secrets never enter source, fixtures, images, logs, or browser bundles.
- Real map browser keys are origin-restricted and attributed.
- OIDC uses Authorization Code + PKCE and secure sessions; no incidental password store.
- Provider outages produce typed degraded states rather than invented success.

## References

- [Stripe Payment Intents](https://docs.stripe.com/payments/payment-intents)
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- [Stripe webhooks](https://docs.stripe.com/webhooks)
- [Mercado Pago PIX](https://www.mercadopago.com.br/developers/pt/docs/checkout-bricks/payment-brick/payment-submission/pix)
- [Mercado Pago notifications](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/notifications)
- [RFC 7636: Proof Key for Code Exchange](https://www.rfc-editor.org/rfc/rfc7636)
- [RFC 9700 OAuth security BCP](https://datatracker.ietf.org/doc/html/rfc9700)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
