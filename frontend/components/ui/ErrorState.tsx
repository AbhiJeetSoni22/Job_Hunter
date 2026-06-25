import { ReactNode } from "react";

interface ErrorStateProps {
  title?: string;
  message: string;
  action?: ReactNode;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  action,
}: ErrorStateProps) {
  return (
    <div
      className="rounded-lg p-5 flex flex-col gap-2"
      style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)" }}
    >
      <p style={{ color: "var(--color-red)", fontWeight: 600, fontSize: "0.9rem" }}>{title}</p>
      <p style={{ color: "var(--color-subtle)", fontSize: "0.85rem" }}>{message}</p>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
