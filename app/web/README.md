# Web application

The Next.js web shell provides a responsive, Brazil-first portfolio demo for
Customer, Restaurant, Courier, and Admin product surfaces. Role links are a
navigation aid only: there is no authentication, payment processing, map
provider, or collection of personal data.

## Local commands

From this directory:

```bash
npm install
npm run dev
npm test -- --run
npm run typecheck
npm run build
```

The demo is intentionally deterministic. Its controls change browser-local
simulated state and API helpers are provider-neutral boundaries for the staged
backend; rendering never requires a network request.
