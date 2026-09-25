"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NavbarAuth } from "@/components/auth/NavbarAuth";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/resume", label: "Resume" },
  { href: "/resume-review", label: "Resume Review" },
];

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  // Close mobile menu whenever route changes
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Lock body scroll when mobile menu is open on small viewports
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileMenuOpen]);

  return (
    <header
      style={{
        background: "var(--color-surface)",
        borderBottom: "1px solid var(--color-border)",
      }}
      className="sticky top-0 z-40"
    >
      <nav className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Brand Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 font-semibold tracking-tight group"
          style={{ color: "var(--color-text)" }}
        >
          <span
            className="w-7 h-7 rounded flex items-center justify-center text-xs font-bold transition-transform group-hover:scale-105"
            style={{
              background: "var(--color-accent)",
              color: "#F5F1E8",
              border: "1px solid var(--color-accent-border)",
              boxShadow: "0 0 10px rgba(143, 23, 51, 0.4)",
            }}
          >
            AI
          </span>
          <span className="text-sm sm:text-base font-bold tracking-tight">
            Internship Hunter
          </span>
        </Link>

        {/* Desktop Navigation Links */}
        <div className="hidden md:flex items-center">
          <ul className="flex items-center gap-1">
            {NAV_LINKS.map(({ href, label }) => {
              const isActive = pathname === href || pathname.startsWith(href + "/");
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className="px-3 py-1.5 rounded-md text-sm transition-colors"
                    style={{
                      color: isActive ? "var(--color-text)" : "var(--color-subtle)",
                      background: isActive ? "var(--color-surface-hover)" : "transparent",
                      border: isActive ? "1px solid var(--color-border)" : "1px solid transparent",
                      fontWeight: isActive ? 600 : 400,
                    }}
                  >
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
          <NavbarAuth />
        </div>

        {/* Mobile Hamburger Toggle Button */}
        <div className="md:hidden flex items-center">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle navigation menu"
            className="p-2 rounded-md transition-colors"
            style={{
              color: "var(--color-text)",
              background: mobileMenuOpen ? "var(--color-surface-hover)" : "transparent",
              border: "1px solid var(--color-border)",
            }}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </nav>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div
          className="md:hidden border-t px-4 pt-3 pb-5 flex flex-col gap-3 fade-up"
          style={{
            background: "var(--color-bg)",
            borderColor: "var(--color-border)",
            boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.8)",
          }}
        >
          <ul className="flex flex-col gap-1">
            {NAV_LINKS.map(({ href, label }) => {
              const isActive = pathname === href || pathname.startsWith(href + "/");
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center px-3 py-2.5 rounded-md text-sm transition-colors"
                    style={{
                      color: isActive ? "var(--color-text)" : "var(--color-subtle)",
                      background: isActive ? "var(--color-surface)" : "transparent",
                      border: isActive ? "1px solid var(--color-border)" : "1px solid transparent",
                      fontWeight: isActive ? 600 : 400,
                    }}
                  >
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>

          <NavbarAuth onAction={() => setMobileMenuOpen(false)} isMobile />
        </div>
      )}
    </header>
  );
}
