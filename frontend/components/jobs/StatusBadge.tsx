import { Badge } from "@/components/ui/Badge";
import type { JobStatus } from "@/lib/types";

interface StatusBadgeProps {
  status: JobStatus;
}

const CONFIG: Record<JobStatus, { label: string; color: "default" | "green" | "amber" | "red" | "sky" | "indigo" }> = {
  saved:     { label: "Saved",     color: "default" },
  applied:   { label: "Applied",   color: "sky"     },
  interview: { label: "Interview", color: "indigo"  },
  offer:     { label: "Offer",     color: "green"   },
  rejected:  { label: "Rejected",  color: "red"     },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, color } = CONFIG[status] ?? CONFIG.saved;
  return <Badge color={color}>{label}</Badge>;
}
