import type { Metadata } from "next";
import { LandingHero } from "@/components/landing/LandingHero";
import { ProductProblem } from "@/components/landing/ProductProblem";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { AiMatchShowcase } from "@/components/landing/AiMatchShowcase";
import { JobDiscoveryPreview } from "@/components/landing/JobDiscoveryPreview";
import { PipelineShowcase } from "@/components/landing/PipelineShowcase";
import { DashboardShowcase } from "@/components/landing/DashboardShowcase";
import { FinalCta } from "@/components/landing/FinalCta";

export const metadata: Metadata = {
  title: { absolute: "Job Hunter – AI-Powered Technical Job & Internship Discovery" },
  description:
    "Upload your resume, aggregate verified engineering listings across RemoteOK and YC Jobs, and let Gemini AI rank opportunities by skill alignment.",
};

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-4 sm:gap-6 pb-12 overflow-x-hidden">
      {/* 1. Hero with animated product preview */}
      <LandingHero />

      {/* 2. Concrete friction breakdown of current job hunt */}
      <ProductProblem />

      {/* 3. Five-step clear product workflow */}
      <HowItWorks />

      {/* 4. Deep-dive into AI match calculation & skill breakdown */}
      <AiMatchShowcase />

      {/* 5. Live discovery card composition with filter tabs */}
      <JobDiscoveryPreview />

      {/* 6. Application pipeline tracking lifecycle */}
      <PipelineShowcase />

      {/* 7. Realistic dashboard cockpit preview */}
      <DashboardShowcase />

      {/* 8. Minimal, high-impact final CTA */}
      <FinalCta />
    </div>
  );
}
