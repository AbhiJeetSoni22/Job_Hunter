import { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: "none" | "sm" | "md" | "lg";
}

const paddingMap = {
  none: "",
  sm:   "p-3",
  md:   "p-5",
  lg:   "p-6",
};

export function Card({ padding = "md", children, className = "", style, ...rest }: CardProps) {
  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "0.625rem",
        ...style,
      }}
      className={`${paddingMap[padding]} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
