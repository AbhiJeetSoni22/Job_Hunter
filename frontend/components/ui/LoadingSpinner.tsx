interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
}

const sizeMap = { sm: "w-4 h-4", md: "w-7 h-7", lg: "w-10 h-10" };

export function LoadingSpinner({ size = "md", label = "Loading…" }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <svg
        className={`animate-spin ${sizeMap[size]}`}
        style={{ color: "var(--color-accent)" }}
        viewBox="0 0 24 24"
        fill="none"
      >
        <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
        <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v3a5 5 0 00-5 5H4z" />
      </svg>
      <span style={{ color: "var(--color-subtle)", fontSize: "0.85rem" }}>{label}</span>
    </div>
  );
}
