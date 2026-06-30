import { Badge } from "@/components/ui/Badge";

interface RecommendationBadgeProps {
  label: string | null;
}

const COLOR_MAP: Record<string, "green" | "sky" | "amber" | "default"> = {
  "Excellent Match": "green",
  "Strong Match": "sky",
  "Potential Match": "amber",
  "Low Match": "default",
};

export function RecommendationBadge({ label }: RecommendationBadgeProps) {
  if (!label) return null;
  return <Badge color={COLOR_MAP[label] ?? "default"}>{label}</Badge>;
}
