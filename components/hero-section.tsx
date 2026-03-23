"use client"

import { CreditCard, Shield, Fingerprint, Globe, Wifi, WifiOff, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export function HeroSection() {
  return (
    <section id="overview" className="relative min-h-screen pt-16">
      {/* Background gradient */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute top-60 -left-40 h-60 w-60 rounded-full bg-accent/15 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 py-24 lg:px-8 lg:py-32">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
          {/* Left Content */}
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary"></span>
              </span>
              Designed for Emerging Markets
            </div>

            <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl text-balance">
              Card-Based Digital Identity & Transaction Platform
            </h1>

            <p className="text-lg text-muted-foreground lg:text-xl leading-relaxed max-w-xl">
              A comprehensive end-to-end system integrating verified digital identity (eKYC), 
              secure biometric authentication, and financial transaction capability — built for 
              Africa and low-connectivity environments.
            </p>

            <div className="flex flex-wrap gap-4">
              <Button size="lg" className="gap-2">
                Explore Architecture
                <ArrowRight className="h-4 w-4" />
              </Button>
              <Button size="lg" variant="outline" className="gap-2">
                View Demo
              </Button>
            </div>

            {/* Key Stats */}
            <div className="grid grid-cols-3 gap-6 pt-8 border-t border-border">
              <div>
                <div className="text-2xl font-bold text-primary">100%</div>
                <div className="text-sm text-muted-foreground">Offline Capable</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-primary">{'<'}$2</div>
                <div className="text-sm text-muted-foreground">Card Issuance</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-primary">3-Factor</div>
                <div className="text-sm text-muted-foreground">Authentication</div>
              </div>
            </div>
          </div>

          {/* Right Content - Card Visualization */}
          <div className="relative">
            <div className="relative mx-auto max-w-md">
              {/* Smart Card */}
              <div className="relative aspect-[1.586/1] rounded-2xl bg-gradient-to-br from-card via-secondary to-card border border-border shadow-2xl overflow-hidden">
                {/* Card chip */}
                <div className="absolute top-8 left-8">
                  <div className="h-10 w-12 rounded-md bg-accent/80 grid grid-cols-3 grid-rows-3 gap-px p-1">
                    {[...Array(9)].map((_, i) => (
                      <div key={i} className="rounded-sm bg-accent-foreground/30" />
                    ))}
                  </div>
                </div>

                {/* Biometric indicator */}
                <div className="absolute top-8 right-8 flex items-center gap-2 rounded-full bg-primary/20 px-3 py-1.5">
                  <Fingerprint className="h-4 w-4 text-primary" />
                  <span className="text-xs font-medium text-primary">Biometric</span>
                </div>

                {/* Card details */}
                <div className="absolute bottom-8 left-8 right-8">
                  <div className="flex items-end justify-between">
                    <div className="space-y-2">
                      <div className="text-xs text-muted-foreground">AFRICARD IDENTITY</div>
                      <div className="font-mono text-lg text-foreground tracking-wider">
                        •••• •••• •••• 4589
                      </div>
                      <div className="text-sm text-muted-foreground">JOHN DOE</div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Globe className="h-5 w-5 text-primary" />
                      <span className="text-xs text-muted-foreground">Cross-Border</span>
                    </div>
                  </div>
                </div>

                {/* Security badge */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-10">
                  <Shield className="h-32 w-32 text-foreground" />
                </div>
              </div>

              {/* Floating features */}
              <div className="absolute -left-4 top-1/4 rounded-lg border border-border bg-card p-3 shadow-lg">
                <div className="flex items-center gap-2">
                  <div className="rounded-full bg-primary/20 p-2">
                    <WifiOff className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <div className="text-xs font-medium text-foreground">Offline Ready</div>
                    <div className="text-xs text-muted-foreground">No internet needed</div>
                  </div>
                </div>
              </div>

              <div className="absolute -right-4 bottom-1/4 rounded-lg border border-border bg-card p-3 shadow-lg">
                <div className="flex items-center gap-2">
                  <div className="rounded-full bg-accent/20 p-2">
                    <Shield className="h-4 w-4 text-accent" />
                  </div>
                  <div>
                    <div className="text-xs font-medium text-foreground">HSM Protected</div>
                    <div className="text-xs text-muted-foreground">Secure key storage</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
