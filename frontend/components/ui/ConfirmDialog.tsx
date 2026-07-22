"use client";

import { useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface ConfirmDialogProps {
  open: boolean;

  title: string;
  description: string;

  confirmText?: string;
  cancelText?: string;

  loading?: boolean;

  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !loading) {
        onCancel();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, loading, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={() => {
        if (!loading) onCancel();
      }}
    >
      <Card
        padding="lg"
        className="card-elevated w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="space-y-5">
          <div>
            <h2 className="text-lg font-semibold">{title}</h2>

            <p
              className="mt-2 text-sm leading-6"
              style={{ color: "var(--color-subtle)" }}
            >
              {description}
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onCancel} disabled={loading}>
              {cancelText}
            </Button>

            <Button variant="danger" loading={loading} onClick={onConfirm}>
              {confirmText}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
