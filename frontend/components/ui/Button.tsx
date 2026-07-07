"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantStyles: Record<Variant, React.CSSProperties> = {
  primary: {
    background: "var(--color-accent)",
    color: "white",
    border: "1px solid transparent",
  },
  secondary: {
    background: "var(--color-surface)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
  },
  ghost: {
    background: "transparent",
    color: "var(--color-subtle)",
    border: "1px solid transparent",
  },
  danger: {
    background: "transparent",
    color: "var(--color-red)",
    border: "1px solid var(--color-red)",
  },
};

const sizeStyles: Record<Size, string> = {
  sm: "px-2.5 py-1 text-xs rounded",
  md: "px-4 py-1.5 text-sm rounded-md",
  lg: "px-5 py-2 text-base rounded-md",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      children,
      style,
      className = "",
      ...rest
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        style={{
          ...variantStyles[variant],
          opacity: disabled || loading ? 0.5 : 1,
          cursor: disabled || loading ? "not-allowed" : "pointer",
          fontWeight: 500,
          transition: "opacity 150ms",
          ...style,
        }}
        className={`inline-flex items-center gap-1.5 select-none btn-fx ${sizeStyles[size]} ${className}`}
        {...rest}
      >
        {loading && (
          <svg
            className="animate-spin w-3.5 h-3.5"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  },
);
