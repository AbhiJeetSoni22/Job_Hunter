import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Default Next.js rewrite-proxy timeout is ~30s — too short for
  // POST /api/scraper/run, which runs a synchronous Playwright scrape
  // (YC Jobs alone can take 40-50s). Without this, Next kills the
  // socket at 30s ("socket hang up" / ECONNRESET) even though the
  // FastAPI backend finishes successfully a few seconds later.
  experimental: {
    proxyTimeout: 120 * 1000, // 2 minutes
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
