import { Card } from "@/components/ui/Card";

interface MatchScoreCardProps {
  score: number;
  summary: string;
}

function scoreColor(score: number): string {
  if (score >= 75) return "var(--color-green)";
  if (score >= 50) return "var(--color-amber)";
  return "var(--color-red)";
}

export function MatchScoreCard({ score, summary }: MatchScoreCardProps) {
  const color = scoreColor(score);
  return (
    <Card padding="lg" hoverable className="fade-up fade-up-1">
      <div className="flex flex-col items-center text-center gap-2">
        <div
          style={{ fontSize: "2.75rem", fontWeight: 800, color, lineHeight: 1 }}
        >
          {score}%
        </div>
        <div
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "var(--color-subtle)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          Resume Match Score
        </div>
        <p
          style={{
            marginTop: "0.5rem",
            fontSize: "0.875rem",
            color: "var(--color-text)",
            maxWidth: "32rem",
          }}
        >
          {summary}
        </p>
      </div>
    </Card>
  );
}
