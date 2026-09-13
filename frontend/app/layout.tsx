import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "@/styles/globals.css";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/auth/AuthContext";
import { NavbarAuth } from "@/components/auth/NavbarAuth";

// TODO: replace with the real production domain once deployed.
const SITE_URL = "https://ai-internship-hunter.example.com";
const SITE_NAME = "AI Internship Hunter";
const SITE_DESCRIPTION =
  "AI-powered internship discovery platform that scrapes internship listings and ranks them by compatibility with your resume using Gemini AI.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_NAME,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  authors: [{ name: SITE_NAME }],
  creator: SITE_NAME,
  keywords: [
    "internship search",
    "AI internship matching",
    "resume matching",
    "Gemini AI",
    "job search",
    "internship tracker",
    "software engineering internships",
  ],
  robots: {
    index: true,
    follow: true,
  },
  manifest: "/site.webmanifest",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: SITE_NAME,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    images: ["/og-image.png"],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f1117",
  colorScheme: "dark",
};

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/resume", label: "Resume" },
  { href: "/resume-review", label: "Resume Review" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <AuthProvider>
          <div className="min-h-screen flex flex-col">
            {/* ── Navbar ────────────────────────────────────────────── */}
            <header
              style={{
                background: "var(--color-surface)",
                borderBottom: "1px solid var(--color-border)",
              }}
              className="sticky top-0 z-40"
            >
              <nav className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
                {/* Brand */}
                <Link
                  href="/"
                  className="flex items-center gap-2 font-semibold tracking-tight"
                  style={{ color: "var(--color-text)" }}
                >
                  <span
                    className="w-7 h-7 rounded-md flex items-center justify-center text-sm font-bold"
                    style={{ background: "var(--color-accent)", color: "white" }}
                  >
                    AI
                  </span>
                  <span>Internship Hunter</span>
                </Link>

                {/* Nav links & Auth */}
                <div className="flex items-center">
                  <ul className="flex items-center gap-1">
                    {NAV_LINKS.map(({ href, label }) => (
                      <li key={href}>
                        <Link
                          href={href}
                          className="px-3 py-1.5 rounded-md text-sm transition-colors"
                          style={{
                            color: "var(--color-subtle)",
                          }}
                        >
                          {label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <NavbarAuth />
                </div>
              </nav>
            </header>

            {/* ── Page content ──────────────────────────────────────── */}
            <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
              {children}
            </main>

            {/* ── Footer ────────────────────────────────────────────── */}
            <footer
              className="text-center py-4 text-xs"
              style={{
                color: "var(--color-muted)",
                borderTop: "1px solid var(--color-border)",
              }}
            >
              © 2026 AI Internship Hunter
            </footer>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
