"use client"

import { useState } from "react"
import { Database, Server, Smartphone, CreditCard, Brain, Lock, ArrowRight, ArrowDown, Layers, Cloud, Shield } from "lucide-react"
import { cn } from "@/lib/utils"

const architectureLayers = [
  {
    id: "frontend",
    title: "Client Layer",
    icon: Smartphone,
    color: "bg-primary",
    components: [
      { name: "Mobile App (React Native)", desc: "Cross-platform mobile application" },
      { name: "Agent Portal (Next.js)", desc: "Web-based merchant/agent interface" },
      { name: "USSD Gateway", desc: "Feature phone support for unbanked users" },
      { name: "Offline SDK", desc: "Local transaction processing" },
    ]
  },
  {
    id: "api",
    title: "API Gateway Layer",
    icon: Cloud,
    color: "bg-accent",
    components: [
      { name: "REST API Gateway", desc: "Rate limiting, authentication" },
      { name: "GraphQL API", desc: "Flexible querying for mobile" },
      { name: "WebSocket Server", desc: "Real-time notifications" },
      { name: "Offline Sync Service", desc: "Conflict resolution & sync" },
    ]
  },
  {
    id: "backend",
    title: "Backend Services",
    icon: Server,
    color: "bg-chart-3",
    components: [
      { name: "Identity Service", desc: "eKYC, verification, enrollment" },
      { name: "Transaction Service", desc: "Payments, authorizations" },
      { name: "Card Management", desc: "Issuance, lifecycle, tokenization" },
      { name: "Notification Service", desc: "SMS, push, email alerts" },
    ]
  },
  {
    id: "ai",
    title: "AI & Security Layer",
    icon: Brain,
    color: "bg-chart-5",
    components: [
      { name: "Biometric Engine", desc: "Face/fingerprint recognition" },
      { name: "Fraud Detection ML", desc: "Real-time anomaly detection" },
      { name: "Liveness Detection", desc: "Anti-spoofing verification" },
      { name: "Risk Scoring Engine", desc: "Dynamic authorization rules" },
    ]
  },
  {
    id: "data",
    title: "Data Layer",
    icon: Database,
    color: "bg-chart-4",
    components: [
      { name: "PostgreSQL", desc: "Primary transactional database" },
      { name: "Redis Cluster", desc: "Caching & session management" },
      { name: "TimescaleDB", desc: "Time-series analytics" },
      { name: "HSM / Secure Element", desc: "Cryptographic key storage" },
    ]
  },
]

export function ArchitectureSection() {
  const [activeLayer, setActiveLayer] = useState<string>("frontend")

  return (
    <section id="architecture" className="py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 lg:px-8">
        {/* Header */}
        <div className="mx-auto max-w-3xl text-center mb-16">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5 text-sm text-muted-foreground mb-4">
            <Layers className="h-4 w-4" />
            System Design
          </div>
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4 text-balance">
            System Architecture
          </h2>
          <p className="text-lg text-muted-foreground">
            A layered microservices architecture designed for scalability, security, and offline-first operation.
          </p>
        </div>

        {/* Architecture Diagram */}
        <div className="grid gap-8 lg:grid-cols-[300px_1fr] items-start">
          {/* Layer Selector */}
          <div className="space-y-2">
            {architectureLayers.map((layer, index) => {
              const Icon = layer.icon
              return (
                <div key={layer.id}>
                  <button
                    onClick={() => setActiveLayer(layer.id)}
                    className={cn(
                      "w-full flex items-center gap-3 rounded-lg p-4 text-left transition-all",
                      activeLayer === layer.id
                        ? "bg-secondary border border-primary/30"
                        : "border border-transparent hover:bg-secondary/50"
                    )}
                  >
                    <div className={cn("rounded-lg p-2", layer.color)}>
                      <Icon className="h-5 w-5 text-foreground" />
                    </div>
                    <div>
                      <div className="font-medium text-foreground">{layer.title}</div>
                      <div className="text-sm text-muted-foreground">
                        {layer.components.length} components
                      </div>
                    </div>
                  </button>
                  {index < architectureLayers.length - 1 && (
                    <div className="flex justify-center py-1">
                      <ArrowDown className="h-4 w-4 text-muted-foreground" />
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Component Details */}
          <div className="rounded-xl border border-border bg-card p-6 lg:p-8">
            {architectureLayers.map((layer) => {
              if (layer.id !== activeLayer) return null
              const Icon = layer.icon
              return (
                <div key={layer.id} className="space-y-6">
                  <div className="flex items-center gap-3">
                    <div className={cn("rounded-lg p-3", layer.color)}>
                      <Icon className="h-6 w-6 text-foreground" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-foreground">{layer.title}</h3>
                      <p className="text-sm text-muted-foreground">Core components and services</p>
                    </div>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    {layer.components.map((component, idx) => (
                      <div
                        key={idx}
                        className="rounded-lg border border-border bg-secondary/50 p-4 hover:border-primary/30 transition-colors"
                      >
                        <div className="font-medium text-foreground mb-1">{component.name}</div>
                        <div className="text-sm text-muted-foreground">{component.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Data Flow Diagram */}
        <div className="mt-16">
          <h3 className="text-xl font-bold text-foreground mb-6 text-center">Data Flow: Registration → Authentication → Transaction</h3>
          <div className="relative">
            <div className="flex flex-col lg:flex-row items-center justify-between gap-4 lg:gap-0">
              {/* Step 1 */}
              <div className="flex-1 rounded-xl border border-border bg-card p-6 text-center">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/20 text-primary">
                  <span className="text-lg font-bold">1</span>
                </div>
                <h4 className="font-semibold text-foreground mb-2">Registration</h4>
                <p className="text-sm text-muted-foreground">
                  eKYC enrollment with biometric capture, ID verification, and card issuance
                </p>
              </div>
              
              <ArrowRight className="hidden lg:block h-6 w-6 text-muted-foreground mx-4 flex-shrink-0" />
              <ArrowDown className="lg:hidden h-6 w-6 text-muted-foreground my-2" />
              
              {/* Step 2 */}
              <div className="flex-1 rounded-xl border border-border bg-card p-6 text-center">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent/20 text-accent">
                  <span className="text-lg font-bold">2</span>
                </div>
                <h4 className="font-semibold text-foreground mb-2">Authentication</h4>
                <p className="text-sm text-muted-foreground">
                  Multi-factor auth: biometric + PIN + device, with liveness detection
                </p>
              </div>
              
              <ArrowRight className="hidden lg:block h-6 w-6 text-muted-foreground mx-4 flex-shrink-0" />
              <ArrowDown className="lg:hidden h-6 w-6 text-muted-foreground my-2" />
              
              {/* Step 3 */}
              <div className="flex-1 rounded-xl border border-border bg-card p-6 text-center">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-chart-3/20 text-chart-3">
                  <span className="text-lg font-bold">3</span>
                </div>
                <h4 className="font-semibold text-foreground mb-2">Transaction</h4>
                <p className="text-sm text-muted-foreground">
                  Tokenized payment with fraud detection, offline queue, and sync
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
