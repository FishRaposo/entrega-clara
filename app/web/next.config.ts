import type { NextConfig } from "next";

type ApiProxyEnvironment = {
  API_INTERNAL_BASE_URL?: string;
};

export function apiProxyDestination(
  environment: ApiProxyEnvironment = process.env,
): string {
  const baseUrl = environment.API_INTERNAL_BASE_URL ?? "http://localhost:8000";
  return `${baseUrl.replace(/\/$/, "")}/api/:path*`;
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: apiProxyDestination(),
      },
    ];
  },
};

export default nextConfig;
