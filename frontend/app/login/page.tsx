"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/components/auth/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      router.push("/dashboard");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Login failed. Please check your credentials.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12 p-6 rounded-xl border shadow-sm" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
      <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--color-text)" }}>
        Sign In
      </h1>
      <p className="text-sm mb-6" style={{ color: "var(--color-subtle)" }}>
        Enter your email and password to access your account.
      </p>

      {error && (
        <div className="p-3 mb-4 rounded text-sm bg-red-950/40 border border-red-800 text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-subtle)" }}>
            Email address
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 rounded-md text-sm border focus:outline-none"
            style={{
              background: "var(--color-bg)",
              borderColor: "var(--color-border)",
              color: "var(--color-text)",
            }}
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-subtle)" }}>
            Password
          </label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 rounded-md text-sm border focus:outline-none"
            style={{
              background: "var(--color-bg)",
              borderColor: "var(--color-border)",
              color: "var(--color-text)",
            }}
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 w-full py-2 px-4 rounded-md text-sm font-medium transition-opacity disabled:opacity-50"
          style={{
            background: "var(--color-accent)",
            color: "white",
          }}
        >
          {submitting ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <p className="mt-6 text-center text-xs" style={{ color: "var(--color-subtle)" }}>
        Don&apos;t have an account?{" "}
        <Link href="/register" className="font-medium hover:underline" style={{ color: "var(--color-accent)" }}>
          Register here
        </Link>
      </p>
    </div>
  );
}
