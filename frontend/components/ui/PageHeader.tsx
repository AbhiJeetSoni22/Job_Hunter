import { ReactNode } from "react";
import { BackButton } from "@/components/ui/BackButton";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  /** Optional — when set (with backLabel), renders a BackButton above the title. */
  backHref?: string;
  backLabel?: string;
}

export function PageHeader({
  title,
  subtitle,
  action,
  backHref,
  backLabel,
}: PageHeaderProps) {
  return (
    <div className="pb-6 mb-6" style={{ borderBottom: "1px solid var(--color-border)" }}>
      {backHref && backLabel && (
        <div className="mb-3">
          <BackButton fallbackHref={backHref} label={backLabel} />
        </div>
      )}
      <div className="flex items-start justify-between gap-4">
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
    </div>
  );
}
