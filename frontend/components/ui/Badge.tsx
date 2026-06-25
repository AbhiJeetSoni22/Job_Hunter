import { HTMLAttributes } from "react";

type BadgeColor = "default" | "green" | "amber" | "red" | "sky" | "indigo";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  color?: BadgeColor;
  dot?: boolean;
}

const colorMap: Record<BadgeColor, { bg: string; text: string }> = {
  default: { bg: "rgba(75,83,99,0.25)",  text: "var(--color-subtle)" },
  green:   { bg: "rgba(34,197,94,0.15)", text: "var(--color-green)"  },
  amber:   { bg: "rgba(245,158,11,0.15)",text: "var(--color-amber)"  },
  red:     { bg: "rgba(239,68,68,0.15)", text: "var(--color-red)"    },
  sky:     { bg: "rgba(56,189,248,0.15)",text: "var(--color-sky)"    },
  indigo:  { bg: "rgba(99,102,241,0.2)", text: "var(--color-accent-h)"},
};

export function Badge({ color = "default", dot = false, children, className = "", ...rest }: BadgeProps) {
  const { bg, text } = colorMap[color];
  return (
    <span
      style={{ background: bg, color: text, fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.03em" }}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full uppercase ${className}`}
      {...rest}
    >
      {dot && <span style={{ background: text }} className="w-1.5 h-1.5 rounded-full" />}
      {children}
    </span>
  );
}
