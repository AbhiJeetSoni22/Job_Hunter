import { HTMLAttributes } from "react";

type BadgeColor = "default" | "green" | "amber" | "red" | "sky" | "indigo";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  color?: BadgeColor;
  dot?: boolean;
}

const colorMap: Record<BadgeColor, { bg: string; text: string; border: string }> = {
  default: { bg: "rgba(255, 255, 255, 0.06)", text: "var(--color-subtle)", border: "rgba(255, 255, 255, 0.12)" },
  green:   { bg: "rgba(34, 197, 94, 0.12)",   text: "var(--color-green)",  border: "rgba(34, 197, 94, 0.28)" },
  amber:   { bg: "rgba(234, 179, 8, 0.12)",   text: "var(--color-amber)",  border: "rgba(234, 179, 8, 0.28)" },
  red:     { bg: "rgba(239, 68, 68, 0.12)",   text: "var(--color-red)",    border: "rgba(239, 68, 68, 0.28)" },
  sky:     { bg: "rgba(56, 189, 248, 0.12)",  text: "var(--color-sky)",    border: "rgba(56, 189, 248, 0.28)" },
  indigo:  { bg: "var(--color-gold-subtle)",  text: "var(--color-gold)",   border: "var(--color-gold-border)" },
};

export function Badge({ color = "default", dot = false, children, className = "", style, ...rest }: BadgeProps) {
  const { bg, text, border } = colorMap[color];
  return (
    <span
      style={{
        background: bg,
        color: text,
        border: `1px solid ${border}`,
        fontSize: "0.6875rem",
        fontWeight: 600,
        letterSpacing: "0.03em",
        ...style,
      }}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full uppercase whitespace-nowrap ${className}`}
      {...rest}
    >
      {dot && <span style={{ background: text }} className="w-1.5 h-1.5 rounded-full flex-shrink-0" />}
      {children}
    </span>
  );
}
