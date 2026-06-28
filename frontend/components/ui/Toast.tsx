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
  success: { bg: "var(--color-surface)", border: "var(--color-green)",  icon: "✅" },
  error:   { bg: "var(--color-surface)", border: "var(--color-red)",    icon: "❌" },
  info:    { bg: "var(--color-surface)", border: "var(--color-accent)", icon: "ℹ️" },
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
        gap: "0.5rem",
        boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
        minWidth: "260px",
        maxWidth: "380px",
        fontSize: "0.85rem",
        color: "var(--color-text)",
      }}
    >
      <span>{icon}</span>
      <span style={{ flex: 1 }}>{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        style={{ color: "var(--color-muted)", background: "none", border: "none", cursor: "pointer", lineHeight: 1 }}
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
      style={{
        position: "fixed",
        bottom: "1.5rem",
        right: "1.5rem",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        alignItems: "flex-end",
      }}
    >
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
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