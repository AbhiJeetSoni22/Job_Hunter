import type { NextConfig } from "next";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  experimental: {
    proxyTimeout: 120 * 1000,
  },

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_BASE_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
