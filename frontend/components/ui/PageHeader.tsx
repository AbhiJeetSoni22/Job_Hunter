import { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function PageHeader({ title, subtitle, action }: PageHeaderProps) {
  return (
    <div
      className="flex items-start justify-between gap-4 pb-6 mb-6"
      style={{ borderBottom: "1px solid var(--color-border)" }}
    >
      <div>
        <h1 style={{ fontSize: "1.375rem", fontWeight: 700, color: "var(--color-text)" }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{ color: "var(--color-subtle)", fontSize: "0.875rem", marginTop: "0.25rem" }}>
            {subtitle}
          </p>
        )}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  );
}
