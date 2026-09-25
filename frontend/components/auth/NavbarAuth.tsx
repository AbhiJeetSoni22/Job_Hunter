"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "./AuthContext";

interface NavbarAuthProps {
  onAction?: () => void;
  isMobile?: boolean;
}

export function NavbarAuth({ onAction, isMobile = false }: NavbarAuthProps) {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="text-xs py-1" style={{ color: "var(--color-subtle)" }}>
        Loading…
      </div>
    );
  }

  if (user) {
    return (
      <div
        className={
          isMobile
            ? "flex flex-col gap-2 pt-3 border-t w-full"
            : "flex items-center gap-3 ml-3 pl-3 border-l"
        }
        style={{ borderColor: "var(--color-border)" }}
      >
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: "var(--color-green)" }} />
          <span className="text-xs font-medium truncate max-w-[180px]" style={{ color: "var(--color-text)" }}>
            {user.name || user.email}
          </span>
        </div>
        <button
          onClick={() => {
            logout();
            onAction?.();
          }}
          className="px-2.5 py-1 rounded text-xs transition-colors hover:brightness-110 btn-fx cursor-pointer text-center"
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
    <div
      className={
        isMobile
          ? "flex flex-col gap-2 pt-3 border-t w-full"
          : "flex items-center gap-2 ml-3 pl-3 border-l"
      }
      style={{ borderColor: "var(--color-border)" }}
    >
      <Link
        href="/login"
        onClick={onAction}
        className="px-3 py-1.5 rounded-md text-sm transition-colors text-center hover:text-white"
        style={{ color: "var(--color-subtle)" }}
      >
        Sign In
      </Link>
      <Link
        href="/register"
        onClick={onAction}
        className="px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors text-center hover:opacity-95 btn-fx"
        style={{
          background: "var(--color-accent)",
          color: "#F5F1E8",
          border: "1px solid var(--color-accent-border)",
        }}
      >
        Get Started
      </Link>
    </div>
  );
}
