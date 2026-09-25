import { Card } from "@/components/ui/Card";
import { MatchQualityTierSkeleton } from "@/components/ui/Skeleton";
import type { MatchQualityBreakdown as MatchQualityBreakdownType } from "@/lib/types";

interface MatchQualityBreakdownProps {
  breakdown: MatchQualityBreakdownType | null;
  loading: boolean;
  /** When false, no active resume exists — quality tiers have no basis. */
  hasResume: boolean;
}

const TIERS: {
  key: keyof MatchQualityBreakdownType;
  label: string;
  range: string;
  color: string;
}[] = [
  {
    key: "excellent",
    label: "Excellent",
    range: "90–100%",
    color: "var(--color-green)",
  },
  { key: "good", label: "Good", range: "75–89%", color: "var(--color-sky)" },
  {
    key: "possible",
    label: "Possible",
    range: "60–74%",
    color: "var(--color-amber)",
  },
  { key: "weak", label: "Weak", range: "< 60%", color: "var(--color-red)" },
];

export function MatchQualityBreakdown({
  breakdown,
  loading,
  hasResume,
}: MatchQualityBreakdownProps) {
  if (!loading && !hasResume) {
    return (
      <Card padding="md" className="card-elevated h-full">
        <h2
          style={{
            fontWeight: 700,
            fontSize: "0.95rem",
            color: "var(--color-text)",
            marginBottom: "0.9rem",
          }}
        >
          Match Quality
        </h2>
        <div className="text-center py-6">
          <p
            style={{
              fontSize: "0.95rem",
              fontWeight: 600,
              color: "var(--color-text)",
            }}
          >
            Resume Required
          </p>
          <p
            style={{
              fontSize: "0.78rem",
              color: "var(--color-muted)",
              marginTop: "0.4rem",
            }}
          >
            Upload a resume to view candidate match quality insights.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="md" className="card-elevated h-full">
      <div className="flex items-center justify-between mb-4">
        <h2
          style={{
            fontWeight: 700,
            fontSize: "0.95rem",
            color: "var(--color-text)",
          }}
        >
          Match Quality
        </h2>
        <span className="text-[0.7rem] uppercase tracking-wider font-medium" style={{ color: "var(--color-muted)" }}>
          Distribution
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
        {loading
          ? TIERS.map((tier) => <MatchQualityTierSkeleton key={tier.key} />)
          : TIERS.map((tier) => (
              <div
                key={tier.key}
                className="text-center p-2.5 sm:p-3 rounded-lg"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <p
                  style={{
                    fontSize: "1.35rem",
                    fontWeight: 800,
                    color: tier.color,
                    lineHeight: 1.2,
                  }}
                >
                  {breakdown ? breakdown[tier.key] : "—"}
                </p>
                <p
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "var(--color-text)",
                    marginTop: "0.2rem",
                  }}
                >
                  {tier.label}
                </p>
                <p style={{ fontSize: "0.6875rem", color: "var(--color-muted)", marginTop: "0.1rem" }}>
                  {tier.range}
                </p>
              </div>
            ))}
      </div>
    </Card>
  );
}
