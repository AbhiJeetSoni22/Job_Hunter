"use client";

import { useRouter } from "next/navigation";
import { hasInAppHistory } from "@/lib/navigationHistory";

interface BackButtonProps {
  /** Route to navigate to when there's no in-app history to go back to. */
  fallbackHref: string;
  /** Visible + accessible label, e.g. "Back to Jobs". */
  label: string;
  className?: string;
}

export function BackButton({ fallbackHref, label, className = "" }: BackButtonProps) {
  const router = useRouter();

  function handleClick() {
    if (hasInAppHistory()) {
      router.back();
    } else {
      router.push(fallbackHref);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`back-btn ${className}`}
      style={{ color: "var(--color-subtle)", fontSize: "0.8125rem", fontWeight: 500 }}
    >
      <svg
        className="back-btn-arrow"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M19 12H5M12 19l-7-7 7-7" />
      </svg>
      {label}
    </button>
  );
}
