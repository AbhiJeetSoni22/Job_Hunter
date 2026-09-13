"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "./AuthContext";

export function NavbarAuth() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="text-xs" style={{ color: "var(--color-subtle)" }}>
        Loading...
      </div>
    );
  }

  if (user) {
    return (
      <div className="flex items-center gap-3 ml-3 pl-3 border-l" style={{ borderColor: "var(--color-border)" }}>
        <span className="text-xs font-medium" style={{ color: "var(--color-text)" }}>
          {user.name || user.email}
        </span>
        <button
          onClick={logout}
          className="px-2.5 py-1 rounded text-xs transition-colors hover:opacity-80"
          style={{
            background: "var(--color-surface-hover)",
            color: "var(--color-subtle)",
            border: "1px solid var(--color-border)",
          }}
        >
          Logout
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 ml-3 pl-3 border-l" style={{ borderColor: "var(--color-border)" }}>
      <Link
        href="/login"
        className="px-3 py-1.5 rounded-md text-sm transition-colors hover:opacity-80"
        style={{ color: "var(--color-subtle)" }}
      >
        Login
      </Link>
      <Link
        href="/register"
        className="px-3 py-1.5 rounded-md text-sm font-medium transition-colors hover:opacity-90"
        style={{
          background: "var(--color-accent)",
          color: "white",
        }}
      >
        Register
      </Link>
    </div>
  );
}
