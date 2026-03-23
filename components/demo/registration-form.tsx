"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Camera, Check, Loader2, User, Phone, CreditCard, Lock } from "lucide-react";
import type { DemoUser } from "@/app/demo/page";

interface RegistrationFormProps {
  onComplete: (user: DemoUser) => void;
  onBack: () => void;
}

export function RegistrationForm({ onComplete, onBack }: RegistrationFormProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [biometricCaptured, setBiometricCaptured] = useState(false);
  
  const [formData, setFormData] = useState({
    fullName: "",
    phone: "",
    nationalId: "",
    email: "",
    pin: "",
    confirmPin: "",
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError("");
  };

  const validateStep1 = () => {
    if (!formData.fullName.trim()) {
      setError("Full name is required");
      return false;
    }
    if (!formData.phone.trim() || formData.phone.length < 10) {
      setError("Valid phone number is required");
      return false;
    }
    if (!formData.nationalId.trim()) {
      setError("National ID is required");
      return false;
    }
    return true;
  };

  const validateStep2 = () => {
    if (!/^\d{4,6}$/.test(formData.pin)) {
      setError("PIN must be 4-6 digits");
      return false;
    }
    if (formData.pin !== formData.confirmPin) {
      setError("PINs do not match");
      return false;
    }
    return true;
  };

  const simulateBiometricCapture = () => {
    setLoading(true);
    setTimeout(() => {
      setBiometricCaptured(true);
      setLoading(false);
    }, 2000);
  };

  const handleSubmit = async () => {
    if (!biometricCaptured) {
      setError("Please capture biometric data");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Generate a simulated biometric data string
      const biometricData = `face_${formData.phone}_${Date.now()}`;
      
      const response = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fullName: formData.fullName,
          phone: formData.phone,
          nationalId: formData.nationalId,
          email: formData.email || undefined,
          pin: formData.pin,
          biometricData,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.message || "Registration failed");
        setLoading(false);
        return;
      }

      // Fetch user details
      const userResponse = await fetch(`/api/users/${data.userId}`);
      const userData = await userResponse.json();

      onComplete(userData.user);
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
            <User className="h-5 w-5 text-primary" />
            User Registration (eKYC)
          </CardTitle>
          <CardDescription>
            Step {step} of 3: {step === 1 ? "Personal Information" : step === 2 ? "Security Setup" : "Biometric Capture"}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {/* Progress Bar */}
          <div className="mb-6 flex gap-2">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-2 flex-1 rounded-full transition-colors ${
                  s <= step ? "bg-primary" : "bg-muted"
                }`}
              />
            ))}
          </div>

          {error && (
            <div className="mb-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* Step 1: Personal Information */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="fullName"
                    value={formData.fullName}
                    onChange={handleInputChange}
                    placeholder="John Doe"
                    className="pl-10"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  Phone Number
                </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="phone"
                    value={formData.phone}
                    onChange={handleInputChange}
                    placeholder="+254712345678"
                    className="pl-10"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  National ID Number
                </label>
                <div className="relative">
                  <CreditCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="nationalId"
                    value={formData.nationalId}
                    onChange={handleInputChange}
                    placeholder="12345678"
                    className="pl-10"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  Email (Optional)
                </label>
                <Input
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="john@example.com"
                />
              </div>

              <Button
                className="w-full"
                onClick={() => validateStep1() && setStep(2)}
              >
                Continue
              </Button>
            </div>
          )}

          {/* Step 2: Security Setup */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  Create PIN (4-6 digits)
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="pin"
                    type="password"
                    value={formData.pin}
                    onChange={handleInputChange}
                    placeholder="Enter PIN"
                    maxLength={6}
                    className="pl-10"
                  />
                </div>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  Confirm PIN
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="confirmPin"
                    type="password"
                    value={formData.confirmPin}
                    onChange={handleInputChange}
                    placeholder="Confirm PIN"
                    maxLength={6}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="rounded-lg bg-muted/50 p-3">
                <p className="text-sm text-muted-foreground">
                  Your PIN will be used as a fallback authentication method when biometric verification is not available.
                </p>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  Back
                </Button>
                <Button
                  className="flex-1"
                  onClick={() => validateStep2() && setStep(3)}
                >
                  Continue
                </Button>
              </div>
            </div>
          )}

          {/* Step 3: Biometric Capture */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex flex-col items-center rounded-lg border-2 border-dashed border-border bg-muted/30 p-8">
                {!biometricCaptured ? (
                  <>
                    <div className="mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-muted">
                      {loading ? (
                        <Loader2 className="h-10 w-10 animate-spin text-primary" />
                      ) : (
                        <Camera className="h-10 w-10 text-muted-foreground" />
                      )}
                    </div>
                    <h3 className="mb-2 font-semibold text-foreground">
                      {loading ? "Capturing..." : "Face Recognition"}
                    </h3>
                    <p className="mb-4 text-center text-sm text-muted-foreground">
                      {loading 
                        ? "Please hold still while we capture your biometric data"
                        : "Click below to simulate biometric capture (face or fingerprint)"
                      }
                    </p>
                    <Button onClick={simulateBiometricCapture} disabled={loading}>
                      {loading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Capturing...
                        </>
                      ) : (
                        <>
                          <Camera className="mr-2 h-4 w-4" />
                          Capture Biometric
                        </>
                      )}
                    </Button>
                  </>
                ) : (
                  <>
                    <div className="mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-primary/10">
                      <Check className="h-10 w-10 text-primary" />
                    </div>
                    <h3 className="mb-2 font-semibold text-foreground">Biometric Captured</h3>
                    <p className="text-center text-sm text-muted-foreground">
                      Your biometric data has been securely captured and converted to an embedding vector.
                    </p>
                  </>
                )}
              </div>

              <div className="rounded-lg bg-muted/50 p-3">
                <h4 className="mb-1 text-sm font-medium text-foreground">Security Note</h4>
                <p className="text-sm text-muted-foreground">
                  We never store raw biometric images. Your face/fingerprint is converted to a 128-dimensional embedding vector that cannot be reversed.
                </p>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setStep(2)} className="flex-1">
                  Back
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleSubmit}
                  disabled={loading || !biometricCaptured}
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Registering...
                    </>
                  ) : (
                    "Complete Registration"
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
