import { Badge } from "@/components/ui/Badge";

interface NeedsRescoreBadgeProps {
  needs: boolean;
}

export function NeedsRescoreBadge({ needs }: NeedsRescoreBadgeProps) {
  if (!needs) return null;
  return (
    <Badge color="amber" dot title="Resume has changed — score may be outdated">
      Rescore needed
    </Badge>
  );
}
