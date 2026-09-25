"use client";

import { useEffect } from "react";

export type ToastVariant = "success" | "error" | "info";

export interface ToastMessage {
  id: number;
  message: string;
  variant: ToastVariant;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: number) => void;
}

const COLORS: Record<ToastVariant, { bg: string; border: string; icon: string }> = {
  success: { bg: "var(--color-surface-elevated)", border: "var(--color-green)", icon: "✓" },
  error:   { bg: "var(--color-surface-elevated)", border: "var(--color-red)",   icon: "✕" },
  info:    { bg: "var(--color-surface-elevated)", border: "var(--color-gold)",  icon: "ℹ" },
};

function Toast({ toast, onDismiss }: { toast: ToastMessage; onDismiss: (id: number) => void }) {
  const { bg, border, icon } = COLORS[toast.variant];

  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(t);
  }, [toast.id, onDismiss]);

  return (
    <div
      role="alert"
      style={{
        background: bg,
        border: `1px solid ${border}`,
        borderRadius: "0.5rem",
        padding: "0.75rem 1rem",
        display: "flex",
        alignItems: "flex-start",
        gap: "0.625rem",
        boxShadow: "0 8px 30px rgba(0, 0, 0, 0.7)",
        minWidth: "260px",
        maxWidth: "min(380px, calc(100vw - 2rem))",
        fontSize: "0.85rem",
        color: "var(--color-text)",
      }}
      className="fade-up"
    >
      <span className="font-bold flex-shrink-0" style={{ color: border }}>{icon}</span>
      <span style={{ flex: 1, lineHeight: 1.4 }}>{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        style={{
          color: "var(--color-muted)",
          background: "none",
          border: "none",
          cursor: "pointer",
          lineHeight: 1,
          padding: "0.25rem",
          margin: "-0.25rem -0.25rem 0 0",
        }}
        className="hover:text-white transition-colors"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

export function ToastContainer({ toasts, onDismiss }: ToastProps) {
  if (toasts.length === 0) return null;
  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none items-end max-w-[calc(100vw-2rem)]"
    >
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <Toast toast={t} onDismiss={onDismiss} />
        </div>
      ))}
    </div>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────────────

import { useState, useCallback } from "react";

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((message: string, variant: ToastVariant = "info") => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, variant }]);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, addToast, dismiss };
}