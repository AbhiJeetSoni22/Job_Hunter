import { Card } from "@/components/ui/Card";
import { SkillChip } from "@/components/resume/SkillChip";

interface SkillTagSectionProps {
  title: string;
  skills: string[];
  missing?: boolean;
  emptyMessage: string;
  animationClass?: string;
}

export function SkillTagSection({
  title,
  skills,
  missing = false,
  emptyMessage,
  animationClass = "",
}: SkillTagSectionProps) {
  return (
    <Card padding="md" className={`card-elevated ${animationClass}`}>
      <h3
        style={{
          fontSize: "0.72rem",
          fontWeight: 700,
          color: missing ? "var(--color-red)" : "var(--color-gold)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
        className="mb-3"
      >
        {title}
      </h3>
      {skills.length === 0 ? (
        <p style={{ fontSize: "0.8125rem", color: "var(--color-muted)" }}>
          {emptyMessage}
        </p>
      ) : (
        <div className="flex flex-wrap gap-1.5 sm:gap-2">
          {skills.map((skill) => (
            <SkillChip key={skill} skill={skill} missing={missing} />
          ))}
        </div>
      )}
    </Card>
  );
}
