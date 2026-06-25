interface SkillChipProps {
  skill: string;
  missing?: boolean;
}

export function SkillChip({ skill, missing = false }: SkillChipProps) {
  return (
    <span
      style={{
        background: missing ? "rgba(239,68,68,0.1)" : "rgba(99,102,241,0.12)",
        color:      missing ? "var(--color-red)"    : "var(--color-accent-h)",
        border:     missing ? "1px solid rgba(239,68,68,0.3)" : "1px solid rgba(99,102,241,0.3)",
        fontSize: "0.75rem",
        fontWeight: 500,
        borderRadius: "0.375rem",
        padding: "0.2rem 0.6rem",
      }}
    >
      {missing && "✗ "}{skill}
    </span>
  );
}
