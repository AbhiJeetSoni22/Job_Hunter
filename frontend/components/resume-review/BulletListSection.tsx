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
    <Card padding="md" className={`card-elevated ${animationClass}`}>
      <h3
        style={{
          fontSize: "0.72rem",
          fontWeight: 700,
          color: "var(--color-gold)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
        className="mb-3"
      >
        {title}
      </h3>
      {items.length === 0 ? (
        <p style={{ fontSize: "0.8125rem", color: "var(--color-muted)" }}>
          {emptyMessage}
        </p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-start gap-2.5"
              style={{ fontSize: "0.85rem", color: "var(--color-text)", lineHeight: 1.6 }}
            >
              <span style={{ color: "var(--color-gold)" }} className="flex-shrink-0 mt-0.5 font-bold">
                •
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
