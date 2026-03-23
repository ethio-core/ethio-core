"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Fingerprint, Lock, Loader2, Phone, Shield, Check } from "lucide-react";
import type { DemoUser, DemoCard } from "@/app/demo/page";

interface LoginFormProps {
  onComplete: (user: DemoUser, card: DemoCard | null, token: string) => void;
  onBack: () => void;
  onRegister: () => void;
  initialPhone?: string;
  initialPin?: string;
}

export function LoginForm({
  onComplete,
  onBack,
  onRegister,
  initialPhone,
  initialPin,
}: LoginFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [phone, setPhone] = useState(initialPhone ?? "");
  const [pin, setPin] = useState(initialPin ?? "");
  const [useBiometric, setUseBiometric] = useState(false);
  const [biometricVerified, setBiometricVerified] = useState(false);

  const simulateBiometricAuth = () => {
    setLoading(true);
    setTimeout(() => {
      setBiometricVerified(true);
      setLoading(false);
    }, 1500);
  };

  const handleLogin = async () => {
    if (!phone) {
      setError("Phone number is required");
      return;
    }

    if (!pin && !biometricVerified) {
      setError("Please enter PIN or use biometric authentication");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const biometricData = biometricVerified ? `face_${phone}_${Date.now()}` : undefined;
      
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone,
          pin: pin || undefined,
          biometricData,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.message || "Login failed");
        setLoading(false);
        return;
      }

      // Get user details including cards
      const userResponse = await fetch(`/api/users/${data.user.id}`);
      const userData = await userResponse.json();

      const activeCard = userData.cards?.find((c: DemoCard) => c.status === "active") || null;
      
      onComplete(userData.user, activeCard, data.token);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg">
      <Button variant="ghost" onClick={onBack} className="mb-4">
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Secure Login
          </CardTitle>
          <CardDescription>
            Authenticate with PIN, biometric, or both for MFA
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-medium text-foreground">
              Phone Number
            </label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={phone}
                onChange={(e) => { setPhone(e.target.value); setError(""); }}
                placeholder="+254712345678"
                className="pl-10"
              />
            </div>
          </div>

          {/* Authentication Method Selection */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setUseBiometric(false)}
              className={`rounded-lg border p-3 text-left transition-colors ${
                !useBiometric 
                  ? "border-primary bg-primary/10" 
                  : "border-border hover:border-primary/50"
              }`}
            >
              <Lock className={`mb-1 h-5 w-5 ${!useBiometric ? "text-primary" : "text-muted-foreground"}`} />
              <p className="text-sm font-medium text-foreground">PIN</p>
              <p className="text-xs text-muted-foreground">Enter your PIN</p>
            </button>

            <button
              onClick={() => setUseBiometric(true)}
              className={`rounded-lg border p-3 text-left transition-colors ${
                useBiometric 
                  ? "border-primary bg-primary/10" 
                  : "border-border hover:border-primary/50"
              }`}
            >
              <Fingerprint className={`mb-1 h-5 w-5 ${useBiometric ? "text-primary" : "text-muted-foreground"}`} />
              <p className="text-sm font-medium text-foreground">Biometric</p>
              <p className="text-xs text-muted-foreground">Face or fingerprint</p>
            </button>
          </div>

          {/* PIN Input */}
          {!useBiometric && (
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                PIN
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type="password"
                  value={pin}
                  onChange={(e) => { setPin(e.target.value); setError(""); }}
                  placeholder="Enter your PIN"
                  maxLength={6}
                  className="pl-10"
                />
              </div>
            </div>
          )}

          {/* Biometric Verification */}
          {useBiometric && (
            <div className="flex flex-col items-center rounded-lg border border-dashed border-border bg-muted/30 p-6">
              {!biometricVerified ? (
                <>
                  <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                    {loading ? (
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    ) : (
                      <Fingerprint className="h-8 w-8 text-muted-foreground" />
                    )}
                  </div>
                  <p className="mb-3 text-sm text-muted-foreground">
                    {loading ? "Verifying biometric..." : "Click to authenticate with biometric"}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={simulateBiometricAuth}
                    disabled={loading}
                  >
                    {loading ? "Verifying..." : "Capture Biometric"}
                  </Button>
                </>
              ) : (
                <>
                  <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                    <Check className="h-8 w-8 text-primary" />
                  </div>
                  <p className="text-sm font-medium text-primary">Biometric Verified</p>
                </>
              )}
            </div>
          )}

          {/* MFA Option */}
          {biometricVerified && (
            <div className="rounded-lg bg-primary/10 p-3">
              <p className="text-sm text-foreground">
                <strong>Enable MFA:</strong> Also enter your PIN for multi-factor authentication
              </p>
              <div className="mt-2">
                <Input
                  type="password"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  placeholder="Enter PIN for MFA (optional)"
                  maxLength={6}
                />
              </div>
            </div>
          )}

          <Button
            className="w-full"
            onClick={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Authenticating...
              </>
            ) : (
              "Login"
            )}
          </Button>

          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              {"Don't have an account? "}
              <button
                onClick={onRegister}
                className="text-primary hover:underline"
              >
                Register now
              </button>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
