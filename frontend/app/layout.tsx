import type { Metadata, Viewport } from "next";
import "@/styles/globals.css";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/auth/AuthContext";
import { Navbar } from "@/components/layout/Navbar";

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
  themeColor: "#070707",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className="dark">
      <body className="min-h-screen flex flex-col bg-[var(--color-bg)] text-[var(--color-text)] antialiased">
        <AuthProvider>
          <div className="min-h-screen flex flex-col">
            {/* ── Navbar ────────────────────────────────────────────── */}
            <Navbar />

            {/* ── Page content ──────────────────────────────────────── */}
            <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
              {children}
            </main>

            {/* ── Footer ────────────────────────────────────────────── */}
            <footer
              className="text-center py-5 text-xs"
              style={{
                color: "var(--color-muted)",
                borderTop: "1px solid var(--color-border)",
                background: "var(--color-bg)",
              }}
            >
              <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
                <span>© 2026 AI Internship Hunter. All rights reserved.</span>
                <span className="text-[0.7rem] uppercase tracking-wider" style={{ color: "var(--color-muted)" }}>
                  Powered by Gemini AI
                </span>
              </div>
            </footer>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
