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
          background: "rgba(239, 68, 68, 0.12)",
          color: "var(--color-red)",
          border: "1px solid rgba(239, 68, 68, 0.3)",
        }
      : variant === "category" && colors
        ? {
            background: colors.bg,
            color: colors.text,
            border: `1px solid ${colors.border}`,
          }
        : {
            background: "rgba(255, 255, 255, 0.05)",
            color: "var(--color-text)",
            border: "1px solid var(--color-border)",
          };

  return (
    <span
      style={{
        ...style,
        fontSize: "0.75rem",
        fontWeight: 500,
        borderRadius: "0.375rem",
        padding: "0.25rem 0.6rem",
        transition: "transform 140ms ease, filter 140ms ease, border-color 140ms ease",
      }}
      className="inline-block hover:brightness-110 select-none whitespace-nowrap"
    >
      {missing && <span className="opacity-70 mr-0.5">✗</span>}
      {skill}
    </span>
  );
}
