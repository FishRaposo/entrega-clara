import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  root: resolve(__dirname, "../.."),
  esbuild: {
    jsx: "automatic",
  },
  resolve: {
    alias: {
      "@testing-library/react": resolve(__dirname, "node_modules/@testing-library/react"),
      "next/navigation": resolve(__dirname, "../../tests/frontend/next-navigation.mock.ts"),
      "react/jsx-dev-runtime": resolve(__dirname, "node_modules/react/jsx-dev-runtime.js"),
      "react/jsx-runtime": resolve(__dirname, "node_modules/react/jsx-runtime.js"),
    },
  },
  server: {
    fs: {
      allow: [resolve(__dirname, "../..")],
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["tests/frontend/**/*.test.{ts,tsx}"],
    setupFiles: [resolve(__dirname, "vitest.setup.ts")],
  },
});
