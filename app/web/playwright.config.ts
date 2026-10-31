import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";

const repoRoot = resolve(__dirname, "../..");

export default defineConfig({
  testDir: resolve(__dirname, "e2e"),
  timeout: 60_000,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    locale: "pt-BR",
    trace: "retain-on-failure",
    // System Edge avoids a large browser download locally; CI overrides
    // with PLAYWRIGHT_CHANNEL unset to use the downloaded headless shell.
    channel: process.env.CI ? undefined : "msedge",
  },
  webServer: [
    {
      command: "python -m uvicorn delivery_platform.api.main:create_app --factory --port 8000",
      cwd: repoRoot,
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run dev -- --port 3000",
      cwd: __dirname,
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
