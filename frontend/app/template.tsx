"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { markPageVisit } from "@/lib/navigationHistory";

export default function Template({ children }: { children: ReactNode }) {
  // Next.js remounts template.tsx on every navigation (unlike layout.tsx),
  // which makes it the right place to record "another page was visited in
  // this tab" for <BackButton>'s history check. Purely additive to the
  // existing page-fade behavior below.
  useEffect(() => {
    markPageVisit();
  }, []);

  return <div className="page-fade">{children}</div>;
}
