"use client"

import { 
  CreditCard, 
  Globe, 
  Wallet, 
  Settings2, 
  Building2, 
  WifiOff, 
  Smartphone,
  Users,
  Shield,
  Banknote,
  Star,
  CheckCircle2,
  ArrowRight
} from "lucide-react"
import { cn } from "@/lib/utils"

const coreFeatures = [
  {
    icon: CreditCard,
    title: "Smart Card Design",
    description: "Dual-interface smart card with embedded Secure Element for biometric-bound authentication and offline transactions.",
    highlights: ["EMV chip + contactless", "On-card biometric matching", "Secure Element storage"]
  },
  {
    icon: WifiOff,
    title: "Offline Transactions",
    description: "Store-and-forward architecture enables payment processing without internet, syncing automatically when connectivity returns.",
    highlights: ["Local transaction queue", "Cryptographic signing", "Conflict resolution"]
  },
  {
    icon: Shield,
    title: "KYC Credential",
    description: "Card serves as portable identity verification, enabling instant onboarding for merchants, banks, and government services.",
    highlights: ["Verified identity proof", "Selective disclosure", "Cross-institution acceptance"]
  },
  {
    icon: Banknote,
    title: "Payment Processing",
    description: "Full-featured payment capabilities including P2P transfers, merchant payments, bill payments, and cash withdrawals.",
    highlights: ["Multi-currency support", "Agent network integration", "QR code payments"]
  }
]

const innovativeFeatures = [
  {
    icon: Globe,
    title: "Identity-as-a-Card",
    description: "Portable KYC passport that works across borders and institutions. Verify once, use everywhere.",
    badge: "Innovation",
    color: "primary"
  },
  {
    icon: Wallet,
    title: "Card-Linked Digital Wallet",
    description: "Seamless integration between physical card and mobile wallet app with synchronized balance and transactions.",
    badge: "Innovation",
    color: "primary"
  },
  {
    icon: Building2,
    title: "Government ID + Payment Convergence",
    description: "Single card serves as national ID, voter registration, healthcare card, and payment instrument.",
    badge: "Innovation",
    color: "accent"
  },
  {
    icon: Globe,
    title: "Cross-Border Usability",
    description: "Regional interoperability allowing card usage across African Economic Community member states.",
    badge: "Coming Soon",
    color: "accent"
  },
  {
    icon: Settings2,
    title: "Programmable Card Rules",
    description: "User-defined spending limits, merchant category restrictions, and risk-based controls.",
    badge: "Innovation",
    color: "primary"
  },
  {
    icon: Users,
    title: "Family & Business Accounts",
    description: "Linked cards for families or businesses with configurable permissions and spending controls.",
    badge: "Innovation",
    color: "primary"
  }
]

const financialInclusionFeatures = [
  {
    icon: Users,
    title: "Unbanked User Focus",
    description: "No bank account required. Card-based stored value account with agent network for cash-in/cash-out."
  },
  {
    icon: Banknote,
    title: "Low-Cost Issuance",
    description: "Under $2 per card through regional manufacturing and optimized Secure Element sourcing."
  },
  {
    icon: WifiOff,
    title: "Offline-First Design",
    description: "Works without internet for days. Essential for rural areas with intermittent connectivity."
  },
  {
    icon: Smartphone,
    title: "Feature Phone Support",
    description: "USSD interface for users without smartphones. No app download required."
  }
]

export function FeaturesSection() {
  return (
    <section id="features" className="py-24 lg:py-32 bg-secondary/30">
      <div className="mx-auto max-w-7xl px-4 lg:px-8">
        {/* Header */}
        <div className="mx-auto max-w-3xl text-center mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground mb-4">
            <Star className="h-4 w-4" />
            Platform Features
          </div>
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4 text-balance">
            Comprehensive Feature Set
          </h2>
          <p className="text-lg text-muted-foreground">
            Built for emerging markets with a focus on accessibility, security, and offline capability.
          </p>
        </div>

        {/* Core Features */}
        <div className="mb-16">
          <h3 className="text-xl font-bold text-foreground mb-6">Core Transaction Features</h3>
          <div className="grid gap-6 md:grid-cols-2">
            {coreFeatures.map((feature, index) => {
              const Icon = feature.icon
              return (
                <div
                  key={index}
                  className="rounded-xl border border-border bg-card p-6 hover:border-primary/30 transition-all group"
                >
                  <div className="flex items-start gap-4">
                    <div className="rounded-lg bg-primary/10 p-3 group-hover:bg-primary/20 transition-colors">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-foreground mb-2">{feature.title}</h4>
                      <p className="text-sm text-muted-foreground mb-3">{feature.description}</p>
                      <div className="flex flex-wrap gap-2">
                        {feature.highlights.map((highlight, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 rounded-full bg-secondary px-3 py-1 text-xs font-medium text-foreground"
                          >
                            <CheckCircle2 className="h-3 w-3 text-primary" />
                            {highlight}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Innovative Features */}
        <div className="mb-16">
          <h3 className="text-xl font-bold text-foreground mb-6">Innovative Features</h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {innovativeFeatures.map((feature, index) => {
              const Icon = feature.icon
              return (
                <div
                  key={index}
                  className="relative rounded-xl border border-border bg-card p-5 hover:border-primary/30 transition-all"
                >
                  <div className={cn(
                    "absolute top-4 right-4 rounded-full px-2 py-0.5 text-xs font-semibold",
                    feature.color === "primary" 
                      ? "bg-primary/10 text-primary" 
                      : "bg-accent/10 text-accent"
                  )}>
                    {feature.badge}
                  </div>
                  <div className="mb-3">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <h4 className="font-semibold text-foreground mb-1">{feature.title}</h4>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              )
            })}
          </div>
        </div>

        {/* Financial Inclusion */}
        <div className="rounded-xl border border-primary/30 bg-primary/5 p-8 lg:p-12">
          <div className="text-center mb-8">
            <h3 className="text-2xl font-bold text-foreground mb-2">Financial Inclusion Focus</h3>
            <p className="text-muted-foreground">
              Designed specifically for underserved populations and low-connectivity environments.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {financialInclusionFeatures.map((feature, index) => {
              const Icon = feature.icon
              return (
                <div key={index} className="text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/20">
                    <Icon className="h-7 w-7 text-primary" />
                  </div>
                  <h4 className="font-semibold text-foreground mb-1">{feature.title}</h4>
                  <p className="text-sm text-muted-foreground">{feature.description}</p>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
