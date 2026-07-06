import { Badge } from "@/components/ui/Badge";

/**
 * Replaces ScoreBadge + RecommendationBadge + NeedsRescoreBadge when no
 * active resume exists — match percentages have no basis without one.
 */
export function ResumeRequiredBadge() {
  return <Badge color="default">Resume Required</Badge>;
}
