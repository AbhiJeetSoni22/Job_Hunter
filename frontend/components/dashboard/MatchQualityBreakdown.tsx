"use client";

import { Card } from "@/components/ui/Card";
import { MatchQualityTierSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
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
  bgSubtle: string;
  borderSubtle: string;
}[] = [
  {
    key: "excellent",
    label: "Excellent",
    range: "90–100%",
    color: "var(--color-green)",
    bgSubtle: "rgba(34, 197, 94, 0.08)",
    borderSubtle: "rgba(34, 197, 94, 0.25)",
  },
  {
    key: "good",
    label: "Good",
    range: "75–89%",
    color: "var(--color-sky)",
    bgSubtle: "rgba(56, 189, 248, 0.08)",
    borderSubtle: "rgba(56, 189, 248, 0.25)",
  },
  {
    key: "possible",
    label: "Possible",
    range: "60–74%",
    color: "var(--color-amber)",
    bgSubtle: "rgba(234, 179, 8, 0.08)",
    borderSubtle: "rgba(234, 179, 8, 0.25)",
  },
  {
    key: "weak",
    label: "Weak",
    range: "< 60%",
    color: "var(--color-red)",
    bgSubtle: "rgba(239, 68, 68, 0.08)",
    borderSubtle: "rgba(239, 68, 68, 0.25)",
  },
];

export function MatchQualityBreakdown({
  breakdown,
  loading,
  hasResume,
}: MatchQualityBreakdownProps) {
  if (!loading && !hasResume) {
    return (
      <Card padding="md" className="card-elevated h-full flex flex-col justify-between border" style={{ borderColor: "var(--color-border)" }}>
        <div>
          <div className="flex items-center justify-between mb-4 pb-3 border-b" style={{ borderColor: "var(--color-border)" }}>
            <h2 className="font-bold text-sm sm:text-base" style={{ color: "var(--color-text)" }}>
              Match Quality
            </h2>
            <span className="text-[0.6875rem] uppercase tracking-wider font-semibold" style={{ color: "var(--color-muted)" }}>
              Distribution
            </span>
          </div>

          <div className="text-center py-8">
            <span className="text-3xl block mb-2">📊</span>
            <p className="font-semibold text-sm" style={{ color: "var(--color-text)" }}>
              Resume Profile Required
            </p>
            <p className="text-xs max-w-xs mx-auto mt-1 leading-relaxed" style={{ color: "var(--color-subtle)" }}>
              Upload your resume once to allow Gemini AI to generate candidate fit distributions.
            </p>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t text-center" style={{ borderColor: "var(--color-border)" }}>
          <Link href="/resume" className="w-full block">
            <Button size="sm" variant="secondary" className="w-full text-xs">
              Upload Resume →
            </Button>
          </Link>
        </div>
      </Card>
    );
  }

  // Calculate total scored for proportional bar
  const totalScored = breakdown
    ? breakdown.excellent + breakdown.good + breakdown.possible + breakdown.weak
    : 0;

  return (
    <Card padding="md" className="card-elevated h-full flex flex-col justify-between border" style={{ borderColor: "var(--color-border)" }}>
      <div>
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-3 border-b" style={{ borderColor: "var(--color-border)" }}>
          <div>
            <h2 className="font-bold text-sm sm:text-base" style={{ color: "var(--color-text)" }}>
              Match Quality
            </h2>
            <p className="text-[0.72rem] mt-0.5" style={{ color: "var(--color-subtle)" }}>
              {totalScored > 0 ? `${totalScored} total scored jobs` : "Tier distribution"}
            </p>
          </div>
          <span className="text-[0.6875rem] uppercase tracking-wider font-semibold" style={{ color: "var(--color-gold)" }}>
            AI Scored
          </span>
        </div>

        {/* Proportional Distribution Split Bar */}
        {!loading && totalScored > 0 && (
          <div className="mb-4">
            <div className="h-2 w-full rounded-full overflow-hidden flex bg-[#141414]">
              {TIERS.map((tier) => {
                const count = breakdown ? breakdown[tier.key] : 0;
                const pct = totalScored > 0 ? (count / totalScored) * 100 : 0;
                if (pct <= 0) return null;
                return (
                  <div
                    key={tier.key}
                    style={{
                      width: `${pct}%`,
                      background: tier.color,
                      transition: "width 400ms ease",
                    }}
                    title={`${tier.label}: ${count} (${Math.round(pct)}%)`}
                  />
                );
              })}
            </div>
          </div>
        )}

        {/* Tier Grid */}
        <div className="grid grid-cols-2 gap-2 sm:gap-2.5">
          {loading
            ? TIERS.map((tier) => <MatchQualityTierSkeleton key={tier.key} />)
            : TIERS.map((tier) => (
                <div
                  key={tier.key}
                  className="p-3 rounded-lg border text-center transition-transform hover:-translate-y-0.5"
                  style={{
                    background: tier.bgSubtle,
                    borderColor: tier.borderSubtle,
                  }}
                >
                  <p
                    className="text-xl font-black leading-tight"
                    style={{ color: tier.color }}
                  >
                    {breakdown ? breakdown[tier.key] : "—"}
                  </p>
                  <p
                    className="text-xs font-bold mt-1"
                    style={{ color: "var(--color-text)" }}
                  >
                    {tier.label}
                  </p>
                  <p
                    className="text-[0.6875rem] font-medium mt-0.5"
                    style={{ color: "var(--color-muted)" }}
                  >
                    {tier.range}
                  </p>
                </div>
              ))}
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-4 pt-3 border-t text-[0.7rem] text-center" style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}>
        Tiers calculate compatibility based on project alignment & skill gaps.
      </div>
    </Card>
  );
}
