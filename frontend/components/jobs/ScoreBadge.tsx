import { Badge } from "@/components/ui/Badge";

interface ScoreBadgeProps {
  score: number | null;
}

function scoreColor(score: number): "green" | "amber" | "red" {
  if (score >= 70) return "green";
  if (score >= 40) return "amber";
  return "red";
}

export function ScoreBadge({ score }: ScoreBadgeProps) {
  if (score === null) {
    return <Badge color="default">Not scored</Badge>;
  }
  return (
    <Badge color={scoreColor(score)} dot>
      {score}% match
    </Badge>
  );
}
