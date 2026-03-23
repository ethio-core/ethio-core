import { Navigation } from "@/components/navigation"
import { HeroSection } from "@/components/hero-section"
import { ArchitectureSection } from "@/components/architecture-section"
import { SecuritySection } from "@/components/security-section"
import { AIBiometricsSection } from "@/components/ai-biometrics-section"
import { FeaturesSection } from "@/components/features-section"
import { ImplementationSection } from "@/components/implementation-section"
import { InnovationSection } from "@/components/innovation-section"
import { Footer } from "@/components/footer"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <Navigation />
      <HeroSection />
      <ArchitectureSection />
      <SecuritySection />
      <AIBiometricsSection />
      <FeaturesSection />
      <ImplementationSection />
      <InnovationSection />
      <Footer />
    </main>
  )
}
