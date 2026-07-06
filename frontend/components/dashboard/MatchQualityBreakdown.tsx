import { Card } from "@/components/ui/Card";
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
      <Card padding="md">
        <h2
          style={{
            fontWeight: 700,
            fontSize: "1rem",
            color: "var(--color-text)",
            marginBottom: "0.9rem",
          }}
        >
          Match Quality
        </h2>
        <div className="text-center py-4">
          <p
            style={{
              fontSize: "0.95rem",
              fontWeight: 600,
              color: "var(--color-subtle)",
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
            Upload a resume to view match quality insights.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="md">
      <h2
        style={{
          fontWeight: 700,
          fontSize: "1rem",
          color: "var(--color-text)",
          marginBottom: "0.9rem",
        }}
      >
        Match Quality
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {TIERS.map((tier) => (
          <div key={tier.key} className="text-center">
            <p
              style={{
                fontSize: "1.4rem",
                fontWeight: 700,
                color: tier.color,
                lineHeight: 1.2,
              }}
            >
              {loading ? "…" : breakdown ? breakdown[tier.key] : "—"}
            </p>
            <p
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                color: "var(--color-text)",
                marginTop: "0.15rem",
              }}
            >
              {tier.label}
            </p>
            <p style={{ fontSize: "0.7rem", color: "var(--color-subtle)" }}>
              {tier.range}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
