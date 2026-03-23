"use client"

import { 
  Lightbulb, 
  Globe, 
  Wallet, 
  Building2, 
  Settings2,
  ArrowRight,
  Sparkles,
  Target,
  Users,
  Shield
} from "lucide-react"
import { Button } from "@/components/ui/button"

const innovations = [
  {
    icon: Globe,
    title: "Identity-as-a-Card (Portable KYC Passport)",
    description: "Revolutionary approach where your verified identity travels with you. Complete eKYC once, then use the card as proof of identity across banks, telcos, government services, and merchants across the region.",
    impact: "Reduces KYC friction by 90% for users opening multiple accounts",
    unique: "First implementation of portable, card-based KYC credential in Africa"
  },
  {
    icon: Wallet,
    title: "Card-Linked Digital Wallet",
    description: "Seamless bridge between physical and digital. The smart card acts as a hardware wallet, syncing automatically with mobile app. Users without smartphones can still transact, while app users get enhanced features.",
    impact: "Serves 100% of users regardless of smartphone access",
    unique: "Hybrid approach supporting both banked and unbanked populations"
  },
  {
    icon: Building2,
    title: "Government ID + Payment Convergence",
    description: "Single multi-purpose card that serves as national ID, voter registration, healthcare card, social benefits disbursement, and payment instrument. Partnerships with governments for national rollout.",
    impact: "Reduces card issuance costs by consolidating 4-5 cards into one",
    unique: "First unified identity-payment platform designed for government adoption"
  },
  {
    icon: Settings2,
    title: "Programmable Card Rules",
    description: "User-defined spending controls, merchant category restrictions, time-based limits, and risk-based authorization. Parents can control children's cards, businesses can set employee expense policies.",
    impact: "Reduces fraud losses by 45% through proactive controls",
    unique: "Consumer-grade programmability previously only available to corporates"
  }
]

const differentiators = [
  {
    title: "Offline-First Architecture",
    description: "Not offline-capable as an afterthought, but designed from ground-up for disconnected operation.",
    icon: Target
  },
  {
    title: "Biometric-Bound Security",
    description: "Card is useless without the registered owner's biometric, eliminating card theft concerns.",
    icon: Shield
  },
  {
    title: "Agent Network Integration",
    description: "Built-in support for cash-in/cash-out through local agent networks common in Africa.",
    icon: Users
  }
]

export function InnovationSection() {
  return (
    <section className="py-24 lg:py-32 bg-secondary/30">
      <div className="mx-auto max-w-7xl px-4 lg:px-8">
        {/* Header */}
        <div className="mx-auto max-w-3xl text-center mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-1.5 text-sm text-accent mb-4">
            <Lightbulb className="h-4 w-4" />
            What Makes It Unique
          </div>
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4 text-balance">
            Innovation Highlights
          </h2>
          <p className="text-lg text-muted-foreground">
            Key differentiators that set AfriCard apart from traditional payment and identity solutions.
          </p>
        </div>

        {/* Main Innovations */}
        <div className="grid gap-8 lg:grid-cols-2 mb-16">
          {innovations.map((innovation, index) => {
            const Icon = innovation.icon
            return (
              <div
                key={index}
                className="rounded-xl border border-border bg-card p-8 hover:border-accent/30 transition-all group"
              >
                <div className="flex items-start gap-4 mb-4">
                  <div className="rounded-lg bg-accent/10 p-3 group-hover:bg-accent/20 transition-colors">
                    <Icon className="h-6 w-6 text-accent" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Sparkles className="h-4 w-4 text-accent" />
                      <span className="text-xs font-semibold text-accent uppercase tracking-wide">Innovation</span>
                    </div>
                    <h3 className="text-xl font-bold text-foreground">{innovation.title}</h3>
                  </div>
                </div>
                
                <p className="text-muted-foreground mb-4 leading-relaxed">
                  {innovation.description}
                </p>
                
                <div className="space-y-3 pt-4 border-t border-border">
                  <div className="flex items-start gap-2">
                    <span className="text-xs font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded">IMPACT</span>
                    <span className="text-sm text-foreground">{innovation.impact}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-xs font-semibold text-accent bg-accent/10 px-2 py-0.5 rounded">UNIQUE</span>
                    <span className="text-sm text-foreground">{innovation.unique}</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Key Differentiators */}
        <div className="rounded-xl border border-primary/30 bg-primary/5 p-8 lg:p-12">
          <h3 className="text-xl font-bold text-foreground mb-8 text-center">Core Differentiators</h3>
          <div className="grid gap-8 md:grid-cols-3">
            {differentiators.map((item, index) => {
              const Icon = item.icon
              return (
                <div key={index} className="text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/20 border-2 border-primary/30">
                    <Icon className="h-8 w-8 text-primary" />
                  </div>
                  <h4 className="font-semibold text-foreground mb-2">{item.title}</h4>
                  <p className="text-sm text-muted-foreground">{item.description}</p>
                </div>
              )
            })}
          </div>
        </div>

        {/* CTA */}
        <div className="mt-16 text-center">
          <h3 className="text-2xl font-bold text-foreground mb-4">Ready to Transform Financial Identity?</h3>
          <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
            AfriCard represents a new paradigm in digital identity and financial services for emerging markets. 
            Join us in building the future of financial inclusion.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Button size="lg" className="gap-2">
              View Full Documentation
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button size="lg" variant="outline">
              Contact Team
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}
