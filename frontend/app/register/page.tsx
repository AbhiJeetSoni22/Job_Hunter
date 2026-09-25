"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/auth/AuthContext";
import { GOOGLE_AUTH_URL } from "@/lib/api";

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { requestOtp, verifyOtp } = useAuth();

  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  useEffect(() => {
    const errorParam = searchParams.get("error");
    if (errorParam) {
      const messages: Record<string, string> = {
        access_denied: "Google authentication was cancelled.",
        invalid_state: "Invalid session state. Please try signing up again.",
        missing_verifier: "Session verifier missing. Please try signing up again.",
        token_exchange_failed: "Failed to exchange token with Google. Please try again.",
        invalid_identity: "Could not verify your Google identity.",
        inactive_user: "This user account is inactive.",
        account_conflict: "This email is already associated with another Google account.",
      };
      setError(messages[errorParam] || `Authentication failed (${errorParam}).`);
    }
  }, [searchParams]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const interval = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [resendCooldown]);

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await requestOtp(email);
      setStep("otp");
      setResendCooldown(60);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to send verification code. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await verifyOtp(email, otp);
      router.push("/dashboard");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Verification failed. Please check your code.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResendOtp = async () => {
    if (resendCooldown > 0 || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      await requestOtp(email);
      setResendCooldown(60);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to resend code.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="w-full max-w-md mx-auto my-6 sm:my-12 p-5 sm:p-8 rounded-xl border card-elevated"
      style={{
        background: "var(--color-surface)",
        borderColor: "var(--color-border)",
      }}
    >
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight mb-1.5" style={{ color: "var(--color-text)" }}>
          {step === "email" ? "Create Account" : "Enter Verification Code"}
        </h1>
        <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--color-subtle)" }}>
          {step === "email"
            ? "Start tracking and matching internships with Google or a quick email code."
            : `We sent a 6-digit verification code to ${email}`}
        </p>
      </div>

      {error && (
        <div
          className="p-3 mb-5 rounded-md text-xs sm:text-sm flex items-start gap-2"
          style={{
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "var(--color-red)",
          }}
        >
          <span className="font-bold">✕</span>
          <span className="flex-1">{error}</span>
        </div>
      )}

      {step === "email" ? (
        <>
          {/* Google OAuth Button */}
          <a
            href={GOOGLE_AUTH_URL}
            className="w-full py-2.5 px-4 rounded-md text-sm font-medium flex items-center justify-center border transition-all hover:brightness-110 cursor-pointer min-h-[42px]"
            style={{
              background: "var(--color-bg)",
              borderColor: "var(--color-border)",
              color: "var(--color-text)",
            }}
          >
            <svg className="w-4 h-4 mr-2.5 flex-shrink-0" viewBox="0 0 24 24">
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
            <div className="relative flex justify-center text-xs uppercase tracking-wider">
              <span
                className="px-2.5 font-medium"
                style={{ background: "var(--color-surface)", color: "var(--color-muted)" }}
              >
                OR
              </span>
            </div>
          </div>

          <form onSubmit={handleRequestOtp} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: "var(--color-subtle)" }}>
                Email address
              </label>
              <input
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-md text-sm border focus:outline-none transition-colors"
                style={{
                  background: "var(--color-bg)",
                  borderColor: "var(--color-border)",
                  color: "var(--color-text)",
                }}
                placeholder="you@example.com"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || !email.trim()}
              className="mt-1 w-full py-2.5 px-4 rounded-md text-sm font-semibold tracking-wide transition-all disabled:opacity-50 btn-fx cursor-pointer min-h-[42px]"
              style={{
                background: "var(--color-accent)",
                color: "#F5F1E8",
                border: "1px solid var(--color-accent-border)",
              }}
            >
              {submitting ? "Sending Code…" : "Continue with Email"}
            </button>
          </form>
        </>
      ) : (
        <form onSubmit={handleVerifyOtp} className="flex flex-col gap-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-subtle)" }}>
                6-Digit Verification Code
              </label>
              <button
                type="button"
                onClick={() => {
                  setStep("email");
                  setOtp("");
                  setError(null);
                }}
                className="text-xs hover:underline cursor-pointer transition-colors"
                style={{ color: "var(--color-gold)" }}
              >
                Change email
              </button>
            </div>
            <input
              type="text"
              required
              autoFocus
              maxLength={6}
              pattern="[0-9]*"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              className="w-full px-3 py-3 rounded-md text-xl sm:text-2xl tracking-[0.25em] sm:tracking-[0.4em] font-mono text-center border focus:outline-none transition-colors"
              style={{
                background: "var(--color-bg)",
                borderColor: "var(--color-border)",
                color: "var(--color-text)",
              }}
              placeholder="123456"
            />
          </div>

          <button
            type="submit"
            disabled={submitting || otp.length !== 6}
            className="mt-1 w-full py-2.5 px-4 rounded-md text-sm font-semibold tracking-wide transition-all disabled:opacity-50 btn-fx cursor-pointer min-h-[42px]"
            style={{
              background: "var(--color-accent)",
              color: "#F5F1E8",
              border: "1px solid var(--color-accent-border)",
            }}
          >
            {submitting ? "Verifying…" : "Verify & Complete Signup"}
          </button>

          <div className="text-center mt-2">
            {resendCooldown > 0 ? (
              <span className="text-xs" style={{ color: "var(--color-muted)" }}>
                Resend code in {resendCooldown}s
              </span>
            ) : (
              <button
                type="button"
                onClick={handleResendOtp}
                disabled={submitting}
                className="text-xs font-medium hover:underline cursor-pointer transition-colors"
                style={{ color: "var(--color-gold)" }}
              >
                Didn&apos;t receive code? Resend
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-md mx-auto mt-12 p-6 text-center text-sm" style={{ color: "var(--color-subtle)" }}>
          Loading…
        </div>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
