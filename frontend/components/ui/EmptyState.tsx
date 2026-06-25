import { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      {icon && (
        <div style={{ color: "var(--color-muted)", fontSize: "2.5rem" }}>{icon}</div>
      )}
      <p style={{ color: "var(--color-text)", fontWeight: 600 }}>{title}</p>
      {description && (
        <p style={{ color: "var(--color-subtle)", fontSize: "0.875rem", maxWidth: "28rem" }}>
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
