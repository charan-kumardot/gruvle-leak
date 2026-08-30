import { MarketingNav } from "@/components/marketing/MarketingNav";
import { Hero } from "@/components/marketing/Hero";
import { ProblemSolution } from "@/components/marketing/ProblemSolution";
import { Features } from "@/components/marketing/Features";
import { LiveDemo } from "@/components/marketing/LiveDemo";
import { HowItWorks } from "@/components/marketing/HowItWorks";
import { TrustSecurity } from "@/components/marketing/TrustSecurity";
import { Pricing } from "@/components/marketing/Pricing";
import { Faq } from "@/components/marketing/Faq";
import { FinalCta } from "@/components/marketing/FinalCta";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <MarketingNav />
      <main className="flex-1">
        <Hero />
        <ProblemSolution />
        <Features />
        <LiveDemo />
        <HowItWorks />
        <TrustSecurity />
        <Pricing />
        <Faq />
        <FinalCta />
      </main>
      <MarketingFooter />
    </div>
  );
}
