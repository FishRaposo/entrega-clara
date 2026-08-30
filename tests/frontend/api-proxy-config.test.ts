import { expect, test } from "vitest";

import { apiProxyDestination } from "../../app/web/next.config";

test("the Next.js proxy targets the API service inside Compose", () => {
  expect(apiProxyDestination({ API_INTERNAL_BASE_URL: "http://api:8000" })).toBe(
    "http://api:8000/api/:path*",
  );
});
