"use client"

import { Shield, Lock, Key, Fingerprint, RefreshCw, Eye, AlertTriangle, Server, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"

const securityFeatures = [
  {
    icon: Key,
    title: "Tokenization",
    description: "Card data is replaced with non-reversible tokens. Actual card numbers are never stored or transmitted after initial tokenization.",
    details: [
      "PCI DSS Level 1 compliant",
      "Token-to-PAN mapping in HSM only",
      "Per-transaction token generation",
      "Merchant-specific token scoping"
    ]
  },
  {
    icon: RefreshCw,
    title: "Dynamic CVV",
    description: "Rotating credentials that change every 60 seconds or per transaction, making stolen data useless for future fraud.",
    details: [
      "TOTP-based rotation algorithm",
      "Time-synced with secure server",
      "Cryptographically generated",
      "Single-use authentication codes"
    ]
  },
  {
    icon: Fingerprint,
    title: "Multi-Factor Auth",
    description: "Three-factor authentication combining something you have (card/device), something you know (PIN), and something you are (biometric).",
    details: [
      "Fingerprint recognition",
      "Face verification with liveness",
      "4-6 digit secure PIN",
      "Device binding & attestation"
    ]
  },
  {
    icon: Eye,
    title: "AI Fraud Detection",
    description: "Real-time machine learning models analyze transaction patterns to detect and prevent fraudulent activities.",
    details: [
      "Behavioral biometrics analysis",
      "Transaction velocity checks",
      "Geolocation anomaly detection",
      "Device fingerprint verification"
    ]
  },
  {
    icon: Server,
    title: "Secure Key Storage",
    description: "Hardware Security Modules (HSM) and Secure Elements provide tamper-resistant storage for cryptographic keys.",
    details: [
      "FIPS 140-2 Level 3 HSM",
      "Card-embedded Secure Element",
      "Key ceremony procedures",
      "Split knowledge protocols"
    ]
  },
  {
    icon: Lock,
    title: "End-to-End Encryption",
    description: "All data in transit and at rest is encrypted using industry-standard algorithms and protocols.",
    details: [
      "TLS 1.3 for all connections",
      "AES-256-GCM encryption",
      "Perfect forward secrecy",
      "Certificate pinning"
    ]
  }
]

export function SecuritySection() {
  return (
    <section id="security" className="py-24 lg:py-32 bg-secondary/30">
      <div className="mx-auto max-w-7xl px-4 lg:px-8">
        {/* Header */}
        <div className="mx-auto max-w-3xl text-center mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary mb-4">
            <Shield className="h-4 w-4" />
            Security Architecture
          </div>
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4 text-balance">
            Enterprise-Grade Security
          </h2>
          <p className="text-lg text-muted-foreground">
            Multi-layered security architecture designed to protect sensitive identity and financial data 
            while maintaining usability for low-literacy users.
          </p>
        </div>

        {/* Security Features Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {securityFeatures.map((feature, index) => {
            const Icon = feature.icon
            return (
              <div
                key={index}
                className="group rounded-xl border border-border bg-card p-6 hover:border-primary/30 transition-all hover:shadow-lg"
              >
                <div className="mb-4 flex items-center gap-3">
                  <div className="rounded-lg bg-primary/10 p-3 group-hover:bg-primary/20 transition-colors">
                    <Icon className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">{feature.title}</h3>
                </div>
                <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                  {feature.description}
                </p>
                <ul className="space-y-2">
                  {feature.details.map((detail, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-primary flex-shrink-0" />
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>

        {/* Security Flow Diagram */}
        <div className="mt-16 rounded-xl border border-border bg-card p-8">
          <h3 className="text-xl font-bold text-foreground mb-6 text-center">Transaction Security Flow</h3>
          <div className="relative overflow-x-auto">
            <div className="min-w-[800px]">
              {/* Flow Steps */}
              <div className="flex items-center justify-between gap-4">
                {[
                  { step: "Card Tap/Insert", desc: "Secure Element reads", icon: "💳" },
                  { step: "Biometric Auth", desc: "Liveness + Face/FP", icon: "👆" },
                  { step: "PIN Entry", desc: "Encrypted at terminal", icon: "🔢" },
                  { step: "Tokenization", desc: "PAN → Token", icon: "🔐" },
                  { step: "Fraud Check", desc: "ML risk scoring", icon: "🛡️" },
                  { step: "HSM Sign", desc: "Cryptographic auth", icon: "✍️" },
                  { step: "Authorization", desc: "Approve/Decline", icon: "✅" },
                ].map((item, idx) => (
                  <div key={idx} className="flex-1 text-center">
                    <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full border-2 border-primary/30 bg-secondary text-2xl">
                      {item.icon}
                    </div>
                    <div className="text-sm font-medium text-foreground">{item.step}</div>
                    <div className="text-xs text-muted-foreground">{item.desc}</div>
                    {idx < 6 && (
                      <div className="absolute top-7 left-0 right-0 h-0.5 bg-primary/20 -z-10" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
