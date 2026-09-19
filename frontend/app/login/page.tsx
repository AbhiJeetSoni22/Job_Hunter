"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/components/auth/AuthContext";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const errorParam = searchParams.get("error");
    if (errorParam) {
      const messages: Record<string, string> = {
        access_denied: "Google authentication was cancelled.",
        invalid_state: "Invalid session state. Please try signing in again.",
        missing_verifier: "Session verifier missing. Please try signing in again.",
        token_exchange_failed: "Failed to exchange token with Google. Please try again.",
        invalid_identity: "Could not verify your Google identity.",
        inactive_user: "This user account is inactive.",
        account_conflict: "This email is already associated with another Google account.",
      };
      setError(messages[errorParam] || `Authentication failed (${errorParam}).`);
    }
  }, [searchParams]);

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

      {/* Google OAuth Button */}
      <a
        href="/api/auth/google"
        className="w-full py-2.5 px-4 rounded-md text-sm font-medium flex items-center justify-center border transition-colors hover:opacity-90 cursor-pointer"
        style={{
          background: "var(--color-surface-hover, rgba(255,255,255,0.05))",
          borderColor: "var(--color-border)",
          color: "var(--color-text)",
        }}
      >
        <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
          />
        </svg>
        Continue with Google
      </a>

      {/* Divider */}
      <div className="relative my-5">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t" style={{ borderColor: "var(--color-border)" }} />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="px-2 font-medium" style={{ background: "var(--color-surface)", color: "var(--color-subtle)" }}>
            OR
          </span>
        </div>
      </div>

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

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-md mx-auto mt-12 p-6 text-center text-sm" style={{ color: "var(--color-subtle)" }}>
          Loading...
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
