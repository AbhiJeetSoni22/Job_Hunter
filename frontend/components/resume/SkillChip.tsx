interface SkillChipProps {
  skill: string;
  missing?: boolean;
  variant?: "default" | "category";
  colors?: { bg: string; text: string; border: string };
}

export function SkillChip({
  skill,
  missing = false,
  variant = "default",
  colors,
}: SkillChipProps) {
  const style =
    missing
      ? {
          background: "rgba(239,68,68,0.1)",
          color: "var(--color-red)",
          border: "1px solid rgba(239,68,68,0.3)",
        }
      : variant === "category" && colors
        ? {
            background: colors.bg,
            color: colors.text,
            border: `1px solid ${colors.border}`,
          }
        : {
            background: "rgba(203,41,87,0.08)",
            color: "var(--color-accent)",
            border: "1px solid rgba(203,41,87,0.25)",
          };

  return (
    <span
      style={{
        ...style,
        fontSize: "0.75rem",
        fontWeight: 500,
        borderRadius: "0.375rem",
        padding: "0.25rem 0.625rem",
        transition: "transform 150ms ease, filter 150ms ease",
      }}
      className="inline-block hover:brightness-110"
    >
      {missing && "✗ "}
      {skill}
    </span>
  );
}
