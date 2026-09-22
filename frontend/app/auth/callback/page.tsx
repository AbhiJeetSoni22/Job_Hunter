"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { exchangeGoogleCode } from "@/lib/api";
import { useAuth } from "@/components/auth/AuthContext";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loginWithToken } = useAuth();
  const [error, setError] = useState<string | null>(null);

  // Guard: Track the code that has been or is currently being exchanged
  const exchangedCodeRef = useRef<string | null>(null);
  const isMountedRef = useRef<boolean>(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const code = searchParams.get("code");
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
      setError(messages[errorParam] || `Google sign in failed (${errorParam}).`);
      return;
    }

    if (!code) {
      setError("Missing authorization code. Please try signing in again.");
      return;
    }

    // Prevent duplicate exchange requests for the same handoff code
    // (guards against React Strict Mode double-invoke, effect re-runs, and dependency updates)
    if (exchangedCodeRef.current === code) {
      return;
    }
    exchangedCodeRef.current = code;

    async function handleExchange() {
      try {
        const tokenResponse = await exchangeGoogleCode(code!);
        await loginWithToken(tokenResponse.access_token);

        // Strip single-use code from browser history so back button/refresh cannot replay it
        if (typeof window !== "undefined" && window.history?.replaceState) {
          window.history.replaceState(null, "", window.location.pathname);
        }

        if (isMountedRef.current) {
          router.replace("/dashboard");
        }
      } catch (err: unknown) {
        if (isMountedRef.current) {
          if (err instanceof Error) {
            setError(err.message);
          } else {
            setError("Failed to complete Google authentication. Please try again.");
          }
        }
      }
    }

    handleExchange();
  }, [searchParams, loginWithToken, router]);

  if (error) {
    return (
      <div
        className="max-w-md mx-auto mt-16 p-6 rounded-xl border shadow-sm text-center"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
      >
        <div
          className="w-12 h-12 mx-auto mb-4 rounded-full flex items-center justify-center font-bold"
          style={{
            background: "rgba(220, 38, 38, 0.1)",
            color: "var(--color-red)",
            border: "1px solid rgba(220, 38, 38, 0.25)",
          }}
        >
          ✕
        </div>
        <h1 className="text-xl font-bold mb-2" style={{ color: "var(--color-text)" }}>
          Authentication Failed
        </h1>
        <p className="text-sm mb-6" style={{ color: "var(--color-subtle)" }}>
          {error}
        </p>
        <Link
          href="/login"
          className="inline-block py-2 px-5 rounded-md text-sm font-medium transition-opacity"
          style={{ background: "var(--color-accent)", color: "white" }}
        >
          Return to Sign In
        </Link>
      </div>
    );
  }

  return (
    <div
      className="max-w-md mx-auto mt-16 p-8 rounded-xl border shadow-sm text-center"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      <div className="inline-block w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mb-4" style={{ borderColor: "var(--color-accent)", borderTopColor: "transparent" }} />
      <h2 className="text-lg font-semibold" style={{ color: "var(--color-text)" }}>
        Completing Google Sign In
      </h2>
      <p className="text-xs mt-1" style={{ color: "var(--color-subtle)" }}>
        Please wait while we verify your identity and restore your session...
      </p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-md mx-auto mt-16 p-8 text-center text-sm" style={{ color: "var(--color-subtle)" }}>
          Loading...
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
