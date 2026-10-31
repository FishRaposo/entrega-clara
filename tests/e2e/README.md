# End-to-end tests

Browser-driven coverage of the full delivery journey plus automated
accessibility checks. Specs live in `app/web/e2e/` — Node resolves
`@playwright/test` from the package that owns the dependency, so the suite
co-locates with the web app it drives.

## Suites

- `app/web/e2e/journeys.spec.ts` — customer browse → checkout → restaurant
  confirm / prepare / ready → courier accept / pickup / route / GPS ping /
  complete → customer sees `delivered` with the deterministic map fallback;
  axe scans of every role page (WCAG 2 A/AA).

## Running

Dev-only dependency — the app itself needs nothing beyond Python + Node.

```powershell
cd app/web
npx playwright install chromium   # one-time browser download
npx playwright test               # boots uvicorn + next dev via webServer
```

The Playwright config launches both servers itself
(`app/web/playwright.config.ts`): the API on `:8000` through the package's
`create_app` factory and the web app on `:3000`. `reuseExistingServer` is on
locally, so running servers are picked up instead of restarted.
