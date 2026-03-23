"use client"

import { Brain, Fingerprint, Eye, Activity, Shield, Zap, Users, TrendingUp, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

const biometricMethods = [
  {
    icon: Fingerprint,
    title: "Fingerprint Recognition",
    description: "High-accuracy fingerprint matching using deep learning models optimized for low-quality sensors.",
    accuracy: "99.7%",
    features: [
      "Works with worn/damaged prints",
      "Anti-spoofing detection",
      "Template-on-card storage",
      "Match-on-device option"
    ]
  },
  {
    icon: Eye,
    title: "Face Verification",
    description: "AI-powered facial recognition with passive liveness detection to prevent photo/video spoofing.",
    accuracy: "99.9%",
    features: [
      "Works in low-light conditions",
      "Mask & glasses tolerance",
      "3D depth analysis",
      "Age progression handling"
    ]
  },
  {
    icon: Activity,
    title: "Behavioral Biometrics",
    description: "Continuous authentication based on typing patterns, device handling, and interaction behaviors.",
    accuracy: "97.5%",
    features: [
      "Keystroke dynamics",
      "Touch pressure patterns",
      "Device motion analysis",
      "Session risk scoring"
    ]
  }
]

const aiCapabilities = [
  {
    title: "Enhanced Security",
    icon: Shield,
    description: "AI models continuously learn from global fraud patterns, adapting to new attack vectors in real-time.",
    benefits: [
      "Zero-day fraud detection",
      "Adaptive threshold tuning",
      "Cross-border pattern sharing",
      "Synthetic ID detection"
    ]
  },
  {
    title: "Fraud Prevention",
    icon: TrendingUp,
    description: "Machine learning analyzes 200+ features per transaction to calculate real-time risk scores.",
    benefits: [
      "Transaction velocity analysis",
      "Merchant category patterns",
      "Geographic impossibility checks",
      "Device reputation scoring"
    ]
  },
  {
    title: "User Experience",
    icon: Users,
    description: "AI optimizes authentication flow based on user behavior, reducing friction for trusted users.",
    benefits: [
      "Risk-based step-up auth",
      "Trusted device recognition",
      "Behavioral trust scoring",
      "Adaptive UX personalization"
    ]
  }
]

export function AIBiometricsSection() {
  return (
    <section id="ai-biometrics" className="py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 lg:px-8">
        {/* Header */}
        <div className="mx-auto max-w-3xl text-center mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-1.5 text-sm text-accent mb-4">
            <Brain className="h-4 w-4" />
            AI & Biometrics
          </div>
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4 text-balance">
            AI-Driven Biometric Authentication
          </h2>
          <p className="text-lg text-muted-foreground">
            State-of-the-art machine learning models for identity verification, fraud detection, 
            and continuous authentication — optimized for resource-constrained environments.
          </p>
        </div>

        {/* Biometric Methods */}
        <div className="mb-16">
          <h3 className="text-xl font-bold text-foreground mb-6 text-center">Biometric Authentication Methods</h3>
          <div className="grid gap-6 md:grid-cols-3">
            {biometricMethods.map((method, index) => {
              const Icon = method.icon
              return (
                <div
                  key={index}
                  className="relative rounded-xl border border-border bg-card p-6 overflow-hidden group hover:border-accent/30 transition-all"
                >
                  {/* Accuracy badge */}
                  <div className="absolute top-4 right-4 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                    {method.accuracy} Accuracy
                  </div>
                  
                  <div className="mb-4">
                    <div className="rounded-lg bg-accent/10 p-3 w-fit group-hover:bg-accent/20 transition-colors">
                      <Icon className="h-6 w-6 text-accent" />
                    </div>
                  </div>
                  
                  <h4 className="text-lg font-semibold text-foreground mb-2">{method.title}</h4>
                  <p className="text-sm text-muted-foreground mb-4">{method.description}</p>
                  
                  <ul className="space-y-2">
                    {method.features.map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <CheckCircle2 className="h-4 w-4 text-accent flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        </div>

        {/* AI Capabilities */}
        <div className="rounded-xl border border-border bg-secondary/30 p-8 lg:p-12">
          <h3 className="text-xl font-bold text-foreground mb-8 text-center">How AI Improves the Platform</h3>
          <div className="grid gap-8 lg:grid-cols-3">
            {aiCapabilities.map((capability, index) => {
              const Icon = capability.icon
              return (
                <div key={index} className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-card p-3 border border-border">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <h4 className="text-lg font-semibold text-foreground">{capability.title}</h4>
                  </div>
                  <p className="text-sm text-muted-foreground">{capability.description}</p>
                  <ul className="space-y-2">
                    {capability.benefits.map((benefit, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-sm text-foreground">
                        <Zap className="h-4 w-4 text-accent flex-shrink-0" />
                        {benefit}
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        </div>

        {/* Liveness Detection */}
        <div className="mt-16 grid gap-8 lg:grid-cols-2 items-center">
          <div className="space-y-6">
            <h3 className="text-2xl font-bold text-foreground">Liveness Detection</h3>
            <p className="text-muted-foreground leading-relaxed">
              Our AI-powered liveness detection prevents presentation attacks using photos, videos, 
              or 3D masks. The system analyzes micro-expressions, eye movement, skin texture, 
              and 3D depth in real-time.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              {[
                { title: "Passive Liveness", desc: "No user action required" },
                { title: "Active Challenges", desc: "Random head movement prompts" },
                { title: "3D Depth Analysis", desc: "Detects flat images/screens" },
                { title: "Texture Analysis", desc: "Identifies printed photos" },
              ].map((item, idx) => (
                <div key={idx} className="rounded-lg border border-border bg-card p-4">
                  <div className="font-medium text-foreground mb-1">{item.title}</div>
                  <div className="text-sm text-muted-foreground">{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
          
          <div className="relative">
            <div className="aspect-square rounded-xl border border-border bg-card p-8 flex items-center justify-center">
              <div className="relative">
                {/* Face outline */}
                <div className="w-48 h-56 rounded-full border-4 border-dashed border-primary/30 flex items-center justify-center">
                  <div className="w-40 h-48 rounded-full border-2 border-primary/50 flex items-center justify-center">
                    <div className="text-6xl">👤</div>
                  </div>
                </div>
                {/* Scanning indicators */}
                <div className="absolute -top-2 -left-2 h-6 w-6 border-t-2 border-l-2 border-primary rounded-tl-lg" />
                <div className="absolute -top-2 -right-2 h-6 w-6 border-t-2 border-r-2 border-primary rounded-tr-lg" />
                <div className="absolute -bottom-2 -left-2 h-6 w-6 border-b-2 border-l-2 border-primary rounded-bl-lg" />
                <div className="absolute -bottom-2 -right-2 h-6 w-6 border-b-2 border-r-2 border-primary rounded-br-lg" />
                {/* Status badges */}
                <div className="absolute -right-16 top-1/4 rounded-full bg-primary/20 px-3 py-1.5 text-xs text-primary font-medium">
                  Depth ✓
                </div>
                <div className="absolute -right-20 top-1/2 rounded-full bg-accent/20 px-3 py-1.5 text-xs text-accent font-medium">
                  Texture ✓
                </div>
                <div className="absolute -right-16 top-3/4 rounded-full bg-chart-3/20 px-3 py-1.5 text-xs text-chart-3 font-medium">
                  Motion ✓
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
