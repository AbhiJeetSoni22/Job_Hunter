import { Card } from "@/components/ui/Card";

interface BulletListSectionProps {
  title: string;
  items: string[];
  emptyMessage: string;
  animationClass?: string;
}

export function BulletListSection({
  title,
  items,
  emptyMessage,
  animationClass = "",
}: BulletListSectionProps) {
  return (
    <Card padding="md" className={animationClass}>
      <h3
        style={{
          fontSize: "0.75rem",
          fontWeight: 700,
          color: "var(--color-subtle)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
        className="mb-3"
      >
        {title}
      </h3>
      {items.length === 0 ? (
        <p style={{ fontSize: "0.8rem", color: "var(--color-muted)" }}>
          {emptyMessage}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-start gap-2"
              style={{ fontSize: "0.85rem", color: "var(--color-text)" }}
            >
              <span style={{ color: "var(--color-accent-h)" }}>•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
