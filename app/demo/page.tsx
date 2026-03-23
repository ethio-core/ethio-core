"use client";

import { useEffect, useState } from "react";
import { RegistrationForm } from "@/components/demo/registration-form";
import { LoginForm } from "@/components/demo/login-form";
import { Dashboard } from "@/components/demo/dashboard";
import { Button } from "@/components/ui/button";
import { CreditCard, Shield, Wifi, WifiOff } from "lucide-react";

export type DemoUser = {
  id: string;
  fullName: string;
  phone: string;
  nationalId: string;
  email?: string;
  kycStatus: string;
  walletBalance: number;
  createdAt: string;
};

export type DemoCard = {
  id: string;
  lastFourDigits: string;
  expiryDate: string;
  status: string;
  dailyLimit: number;
  spentToday: number;
};

export default function DemoPage() {
  const [step, setStep] = useState<"welcome" | "register" | "login" | "dashboard">("welcome");
  const [user, setUser] = useState<DemoUser | null>(null);
  const [card, setCard] = useState<DemoCard | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  const [seedLoading, setSeedLoading] = useState(false);
  const [demoAccounts, setDemoAccounts] = useState<Array<{ phone: string; pin: string; fullName: string }>>([]);
  const [loginPrefill, setLoginPrefill] = useState<{ phone: string; pin: string } | null>(null);

  useEffect(() => {
    // Seed demo accounts for the /demo flow (works in-memory for MVP).
    setSeedLoading(true);
    fetch("/api/seed-demo", { method: "POST" })
      .then(async (res) => {
        const data = await res.json();
        if (data?.success && Array.isArray(data?.accounts)) {
          setDemoAccounts(data.accounts);
        }
      })
      .catch(() => {
        // Non-blocking: if seeding fails, user can still register/login.
      })
      .finally(() => setSeedLoading(false));
  }, []);

  const handleRegistrationComplete = (userData: DemoUser) => {
    setUser(userData);
    setStep("login");
    setLoginPrefill(null);
  };

  const handleLoginComplete = (userData: DemoUser, cardData: DemoCard | null, authToken: string) => {
    setUser(userData);
    setCard(cardData);
    setToken(authToken);
    setStep("dashboard");
  };

  const handleLogout = () => {
    setUser(null);
    setCard(null);
    setToken(null);
    setStep("welcome");
    setLoginPrefill(null);
  };

  const handleCardCreated = (cardData: DemoCard) => {
    setCard(cardData);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
                <CreditCard className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-foreground">AfriCard MVP Demo</h1>
                <p className="text-xs text-muted-foreground">Functional Identity & Transaction System</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Offline Toggle */}
              <button
                onClick={() => setIsOffline(!isOffline)}
                className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                  isOffline 
                    ? "bg-accent/20 text-accent" 
                    : "bg-primary/20 text-primary"
                }`}
              >
                {isOffline ? (
                  <>
                    <WifiOff className="h-4 w-4" />
                    Offline Mode
                  </>
                ) : (
                  <>
                    <Wifi className="h-4 w-4" />
                    Online
                  </>
                )}
              </button>

              {user && (
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm font-medium text-foreground">{user.fullName}</p>
                    <p className="text-xs text-muted-foreground">${user.walletBalance.toFixed(2)}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleLogout}>
                    Logout
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8">
        {step === "welcome" && (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="mb-8 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10">
              <Shield className="h-10 w-10 text-primary" />
            </div>
            <h2 className="mb-4 text-center text-3xl font-bold text-foreground">
              Welcome to the AfriCard MVP
            </h2>
            <p className="mb-8 max-w-md text-center text-muted-foreground">
              Experience the complete user flow: Register with eKYC, create a virtual card, 
              authenticate with biometrics, and process transactions.
            </p>
            
            <div className="mb-8 grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-border bg-card p-4">
                <h3 className="mb-2 font-semibold text-foreground">New User?</h3>
                <p className="mb-4 text-sm text-muted-foreground">
                  Register with your details and biometric data to create your digital identity.
                </p>
                <Button onClick={() => setStep("register")} className="w-full">
                  Register Now
                </Button>
              </div>
              
              <div className="rounded-lg border border-border bg-card p-4">
                <h3 className="mb-2 font-semibold text-foreground">Existing User?</h3>
                <p className="mb-4 text-sm text-muted-foreground">
                  Login with your phone number and PIN or biometric authentication.
                </p>
                <Button variant="outline" onClick={() => setStep("login")} className="w-full">
                  Login
                </Button>
              </div>
            </div>

            <div className="rounded-lg border border-border bg-card/50 p-6">
              <h3 className="mb-4 text-center font-semibold text-foreground">Demo Flow</h3>
              <div className="flex flex-wrap items-center justify-center gap-4">
                {[
                  { step: 1, label: "Register (eKYC)" },
                  { step: 2, label: "Create Card" },
                  { step: 3, label: "Login (MFA)" },
                  { step: 4, label: "Make Payment" },
                ].map((item, index) => (
                  <div key={item.step} className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                      {item.step}
                    </div>
                    <span className="text-sm text-foreground">{item.label}</span>
                    {index < 3 && (
                      <span className="hidden text-muted-foreground sm:inline">→</span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 rounded-lg border border-border bg-card p-5">
              <h3 className="mb-3 text-center font-semibold text-foreground">Demo Accounts</h3>
              {seedLoading ? (
                <p className="text-center text-sm text-muted-foreground">Preparing demo accounts...</p>
              ) : demoAccounts.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {demoAccounts.map((a) => (
                    <div
                      key={a.phone}
                      className="rounded-lg border border-border bg-card p-3"
                    >
                      <p className="text-sm font-medium text-foreground">{a.fullName}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Phone: <span className="font-mono">{a.phone}</span>
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        PIN: <span className="font-mono">{a.pin}</span>
                      </p>
                      <div className="mt-3">
                        <Button
                          className="w-full"
                          onClick={() => {
                            setLoginPrefill({ phone: a.phone, pin: a.pin });
                            setStep("login");
                          }}
                        >
                          Use Account
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-sm text-muted-foreground">
                  Demo accounts not available. You can register instead.
                </p>
              )}
            </div>
          </div>
        )}

        {step === "register" && (
          <RegistrationForm 
            onComplete={handleRegistrationComplete}
            onBack={() => setStep("welcome")}
          />
        )}

        {step === "login" && (
          <LoginForm 
            onComplete={handleLoginComplete}
            onBack={() => {
              setStep("welcome");
              setLoginPrefill(null);
            }}
            onRegister={() => {
              setStep("register");
              setLoginPrefill(null);
            }}
            initialPhone={loginPrefill?.phone}
            initialPin={loginPrefill?.pin}
          />
        )}

        {step === "dashboard" && user && token && (
          <Dashboard 
            user={user}
            card={card}
            token={token}
            isOffline={isOffline}
            onCardCreated={handleCardCreated}
            onUserUpdate={setUser}
          />
        )}
      </main>
    </div>
  );
}
