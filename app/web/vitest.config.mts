import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const here = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: resolve(here, "../.."),
  plugins: [react()],
  resolve: {
    alias: {
      "@testing-library/react": resolve(here, "node_modules/@testing-library/react"),
      "next/navigation": resolve(here, "../../tests/frontend/next-navigation.mock.ts"),
      "react/jsx-dev-runtime": resolve(here, "node_modules/react/jsx-dev-runtime.js"),
      "react/jsx-runtime": resolve(here, "node_modules/react/jsx-runtime.js"),
    },
  },
  server: {
    fs: {
      allow: [resolve(here, "../..")],
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/frontend/**/*.test.{ts,tsx}"],
    setupFiles: [resolve(here, "vitest.setup.ts")],
  },
});
