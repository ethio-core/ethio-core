"use client"

import { useState } from "react"
import { 
  Code2, 
  Database, 
  Server, 
  Smartphone, 
  Brain, 
  Rocket, 
  CheckCircle2,
  ChevronRight,
  Layers,
  Clock,
  Target,
  Zap
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const techStack = {
  frontend: [
    { name: "React Native", purpose: "Cross-platform mobile app" },
    { name: "Next.js 16", purpose: "Web portal & admin dashboard" },
    { name: "Expo", purpose: "Mobile development toolkit" },
    { name: "TailwindCSS", purpose: "Styling framework" },
  ],
  backend: [
    { name: "Node.js + Fastify", purpose: "High-performance API server" },
    { name: "GraphQL + REST", purpose: "Flexible API layer" },
    { name: "Redis Cluster", purpose: "Caching & sessions" },
    { name: "PostgreSQL", purpose: "Primary database" },
  ],
  ai: [
    { name: "TensorFlow Lite", purpose: "On-device biometrics" },
    { name: "AWS Rekognition", purpose: "Cloud face verification" },
    { name: "Scikit-learn", purpose: "Fraud detection models" },
    { name: "ONNX Runtime", purpose: "Cross-platform ML inference" },
  ],
  infrastructure: [
    { name: "Kubernetes", purpose: "Container orchestration" },
    { name: "AWS / Azure", purpose: "Cloud infrastructure" },
    { name: "Thales HSM", purpose: "Hardware security modules" },
    { name: "Kafka", purpose: "Event streaming" },
  ]
}

const mvpPhases = [
  {
    phase: "Phase 1",
    title: "Foundation",
    duration: "Weeks 1-4",
    tasks: [
      "Set up cloud infrastructure (AWS/Azure)",
      "Deploy PostgreSQL + Redis cluster",
      "Implement core API gateway with auth",
      "Create basic mobile app scaffold",
      "Integrate HSM for key management"
    ]
  },
  {
    phase: "Phase 2",
    title: "Identity & Cards",
    duration: "Weeks 5-8",
    tasks: [
      "Build eKYC enrollment flow",
      "Integrate face/fingerprint capture",
      "Implement card issuance service",
      "Create tokenization engine",
      "Deploy biometric matching engine"
    ]
  },
  {
    phase: "Phase 3",
    title: "Transactions",
    duration: "Weeks 9-12",
    tasks: [
      "Build payment processing engine",
      "Implement offline transaction queue",
      "Create merchant/agent portal",
      "Integrate fraud detection ML",
      "Build USSD gateway for feature phones"
    ]
  },
  {
    phase: "Phase 4",
    title: "Launch Prep",
    duration: "Weeks 13-16",
    tasks: [
      "Security audit & penetration testing",
      "Load testing & optimization",
      "Regulatory compliance review",
      "Pilot deployment with test users",
      "Documentation & training materials"
    ]
  }
]

const demoScenario = [
  {
    step: 1,
    title: "User Registration",
    description: "New user approaches an agent, provides ID, captures biometrics (face + fingerprint), receives smart card instantly.",
    demo: "Show mobile app enrollment flow with live camera"
  },
  {
    step: 2,
    title: "Card Activation",
    description: "User activates card with PIN setup and biometric binding. Card is now ready for transactions.",
    demo: "Display card activation UI and PIN entry"
  },
  {
    step: 3,
    title: "Offline Payment",
    description: "User makes payment at merchant without internet. Transaction is signed locally and queued for sync.",
    demo: "Show terminal in offline mode processing payment"
  },
  {
    step: 4,
    title: "KYC Verification",
    description: "User presents card at another institution. Their verified identity is confirmed instantly.",
    demo: "Display identity verification screen with green checkmark"
  }
]

const apiEndpoints = [
  { method: "POST", endpoint: "/api/v1/identity/enroll", description: "Start eKYC enrollment process" },
  { method: "POST", endpoint: "/api/v1/identity/verify", description: "Verify identity with biometrics" },
  { method: "POST", endpoint: "/api/v1/cards/issue", description: "Issue new card to verified user" },
  { method: "POST", endpoint: "/api/v1/cards/activate", description: "Activate card with PIN binding" },
  { method: "POST", endpoint: "/api/v1/transactions/authorize", description: "Authorize payment transaction" },
  { method: "POST", endpoint: "/api/v1/transactions/offline-sync", description: "Sync offline transactions" },
  { method: "GET", endpoint: "/api/v1/user/balance", description: "Get account balance" },
  { method: "POST", endpoint: "/api/v1/fraud/score", description: "Get real-time risk score" },
]

export function ImplementationSection() {
  const [activeTab, setActiveTab] = useState<"stack" | "mvp" | "demo" | "api">("stack")

  return (
    <section id="implementation" className="py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 lg:px-8">
        {/* Header */}
        <div className="mx-auto max-w-3xl text-center mb-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground mb-4">
            <Rocket className="h-4 w-4" />
            Implementation Plan
          </div>
          <h2 className="text-3xl font-bold text-foreground sm:text-4xl mb-4 text-balance">
            From Concept to Production
          </h2>
          <p className="text-lg text-muted-foreground">
            A practical roadmap for building and deploying the AfriCard platform.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap justify-center gap-2 mb-12">
          {[
            { id: "stack", label: "Tech Stack", icon: Code2 },
            { id: "mvp", label: "MVP Plan", icon: Target },
            { id: "demo", label: "Demo Scenario", icon: Zap },
            { id: "api", label: "API Design", icon: Layers },
          ].map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={cn(
                  "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all",
                  activeTab === tab.id
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-muted-foreground hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Tech Stack Tab */}
        {activeTab === "stack" && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {Object.entries(techStack).map(([category, items]) => (
              <div key={category} className="rounded-xl border border-border bg-card p-6">
                <div className="flex items-center gap-2 mb-4">
                  {category === "frontend" && <Smartphone className="h-5 w-5 text-primary" />}
                  {category === "backend" && <Server className="h-5 w-5 text-primary" />}
                  {category === "ai" && <Brain className="h-5 w-5 text-primary" />}
                  {category === "infrastructure" && <Database className="h-5 w-5 text-primary" />}
                  <h3 className="font-semibold text-foreground capitalize">{category}</h3>
                </div>
                <ul className="space-y-3">
                  {items.map((item, idx) => (
                    <li key={idx}>
                      <div className="font-medium text-foreground text-sm">{item.name}</div>
                      <div className="text-xs text-muted-foreground">{item.purpose}</div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {/* MVP Plan Tab */}
        {activeTab === "mvp" && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {mvpPhases.map((phase, index) => (
              <div
                key={index}
                className="rounded-xl border border-border bg-card p-6 relative"
              >
                <div className="absolute -top-3 left-4 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">
                  {phase.phase}
                </div>
                <div className="mt-2 mb-4">
                  <h3 className="text-lg font-semibold text-foreground">{phase.title}</h3>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    {phase.duration}
                  </div>
                </div>
                <ul className="space-y-2">
                  {phase.tasks.map((task, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                      {task}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {/* Demo Scenario Tab */}
        {activeTab === "demo" && (
          <div className="max-w-4xl mx-auto">
            <div className="rounded-xl border border-border bg-card p-8">
              <h3 className="text-xl font-bold text-foreground mb-6 text-center">
                Hackathon Demo Flow
              </h3>
              <div className="space-y-6">
                {demoScenario.map((item, index) => (
                  <div key={index} className="flex gap-6">
                    <div className="flex-shrink-0">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">
                        {item.step}
                      </div>
                    </div>
                    <div className="flex-1 pb-6 border-b border-border last:border-0 last:pb-0">
                      <h4 className="font-semibold text-foreground mb-1">{item.title}</h4>
                      <p className="text-sm text-muted-foreground mb-2">{item.description}</p>
                      <div className="inline-flex items-center gap-2 rounded-full bg-accent/10 px-3 py-1 text-xs text-accent">
                        <Zap className="h-3 w-3" />
                        {item.demo}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* API Design Tab */}
        {activeTab === "api" && (
          <div className="max-w-4xl mx-auto">
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="border-b border-border bg-secondary/50 px-6 py-4">
                <h3 className="font-semibold text-foreground">Key API Endpoints</h3>
                <p className="text-sm text-muted-foreground">RESTful API design for core platform operations</p>
              </div>
              <div className="divide-y divide-border">
                {apiEndpoints.map((endpoint, index) => (
                  <div key={index} className="flex items-center gap-4 px-6 py-3">
                    <span
                      className={cn(
                        "rounded px-2 py-1 text-xs font-mono font-semibold",
                        endpoint.method === "GET"
                          ? "bg-primary/20 text-primary"
                          : "bg-accent/20 text-accent"
                      )}
                    >
                      {endpoint.method}
                    </span>
                    <code className="text-sm font-mono text-foreground flex-1">
                      {endpoint.endpoint}
                    </code>
                    <span className="text-sm text-muted-foreground hidden md:block">
                      {endpoint.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
