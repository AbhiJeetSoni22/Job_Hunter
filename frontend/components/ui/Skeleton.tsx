import { HTMLAttributes } from "react";

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  rounded?: string;
}

/** Single shimmering placeholder block. Compose these for card/row skeletons. */
export function Skeleton({
  width = "100%",
  height = "1rem",
  rounded,
  className = "",
  style,
  ...rest
}: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius: rounded, ...style }}
      aria-hidden="true"
      {...rest}
    />
  );
}

/** Placeholder matching the dashboard StatCard layout. */
export function StatCardSkeleton() {
  return (
    <div
      className="p-5 h-full"
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "0.625rem",
      }}
    >
      <Skeleton width="60%" height="0.65rem" />
      <div className="mt-3">
        <Skeleton width="45%" height="1.6rem" />
      </div>
    </div>
  );
}

/** Placeholder row matching a Top Matches list item. */
export function TopMatchRowSkeleton() {
  return (
    <div
      className="flex items-center gap-4 px-5 py-3"
      style={{ borderBottom: "1px solid var(--color-border)" }}
    >
      <Skeleton width="1.25rem" height="0.75rem" />
      <div className="flex-1 min-w-0">
        <Skeleton width="55%" height="0.875rem" />
        <div className="mt-2">
          <Skeleton width="35%" height="0.775rem" />
        </div>
      </div>
      <Skeleton width="3.5rem" height="1.5rem" rounded="0.375rem" />
    </div>
  );
}

/** Placeholder matching a Match Quality tier cell. */
export function MatchQualityTierSkeleton() {
  return (
    <div className="flex flex-col items-center gap-2">
      <Skeleton width="2.2rem" height="1.4rem" />
      <Skeleton width="3.5rem" height="0.75rem" />
      <Skeleton width="2.8rem" height="0.7rem" />
    </div>
  );
}

/** Placeholder matching a JobCard row. */
export function JobCardSkeleton() {
  return (
    <div
      className="p-4"
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "0.625rem",
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <Skeleton width="45%" height="0.95rem" />
          <div className="mt-2">
            <Skeleton width="30%" height="0.85rem" />
          </div>
          <div className="flex gap-1.5 mt-3">
            <Skeleton width="4rem" height="1.35rem" rounded="0.375rem" />
            <Skeleton width="3.5rem" height="1.35rem" rounded="0.375rem" />
            <Skeleton width="3rem" height="1.35rem" rounded="0.375rem" />
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <Skeleton width="3.5rem" height="0.75rem" />
          <div className="mt-2">
            <Skeleton width="3rem" height="0.75rem" />
          </div>
        </div>
      </div>
    </div>
  );
}
