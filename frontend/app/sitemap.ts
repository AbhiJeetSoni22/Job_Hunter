import type { MetadataRoute } from "next";

// TODO: replace with the real production domain once deployed.
const BASE_URL = "https://ai-internship-hunter.example.com";

/**
 * Static top-level routes only. /jobs/[id] pages are per-user, dynamically
 * scraped data (not meant for public search-engine indexing), so they are
 * intentionally left out rather than fetched at build time.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const routes = ["/", "/dashboard", "/jobs", "/resume", "/resume-review"];

  return routes.map((route) => ({
    url: `${BASE_URL}${route}`,
    lastModified: new Date(),
    changeFrequency: "weekly",
    priority: route === "/" ? 1 : 0.6,
  }));
}
