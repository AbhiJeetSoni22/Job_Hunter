"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/components/auth/AuthContext";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await register({ name, email, password });
      router.push("/dashboard");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Registration failed. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12 p-6 rounded-xl border shadow-sm" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}>
      <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--color-text)" }}>
        Create an Account
      </h1>
      <p className="text-sm mb-6" style={{ color: "var(--color-subtle)" }}>
        Sign up to start tracking and matching internships.
      </p>

      {error && (
        <div className="p-3 mb-4 rounded text-sm bg-red-950/40 border border-red-800 text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-subtle)" }}>
            Full Name
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 rounded-md text-sm border focus:outline-none"
            style={{
              background: "var(--color-bg)",
              borderColor: "var(--color-border)",
              color: "var(--color-text)",
            }}
            placeholder="Jane Doe"
          />
        </div>

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
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 rounded-md text-sm border focus:outline-none"
            style={{
              background: "var(--color-bg)",
              borderColor: "var(--color-border)",
              color: "var(--color-text)",
            }}
            placeholder="At least 8 characters"
          />
        </div>

        <div>
          <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-subtle)" }}>
            Confirm Password
          </label>
          <input
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
          {submitting ? "Creating Account..." : "Register"}
        </button>
      </form>

      <p className="mt-6 text-center text-xs" style={{ color: "var(--color-subtle)" }}>
        Already have an account?{" "}
        <Link href="/login" className="font-medium hover:underline" style={{ color: "var(--color-accent)" }}>
          Sign in here
        </Link>
      </p>
    </div>
  );
}
