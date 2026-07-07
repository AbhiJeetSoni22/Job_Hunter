import type { Metadata } from "next";
import Link from "next/link";
import "@/styles/globals.css";
import type { ReactNode } from "react";
export const metadata: Metadata = {
  title: {
    default: "AI Internship Hunter",
    template: "%s | AI Internship Hunter",
  },
  description: "Find and score software engineering internships with AI",
};

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/resume", label: "Resume" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
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

              {/* Nav links */}
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
      </body>
    </html>
  );
}
