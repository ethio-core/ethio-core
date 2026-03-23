"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  X, 
  Send, 
  Loader2, 
  AlertTriangle, 
  CheckCircle, 
  Shield,
  Fingerprint,
  Check,
  Clock
} from "lucide-react";
import type { DemoUser, DemoCard } from "@/app/demo/page";

interface PaymentModalProps {
  user: DemoUser;
  card: DemoCard;
  isOffline: boolean;
  onClose: () => void;
  onComplete: () => void;
}

export function PaymentModal({ user, card, isOffline, onClose, onComplete }: PaymentModalProps) {
  const [step, setStep] = useState<"details" | "verify" | "processing" | "result">("details");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
    fraudAlert?: boolean;
    transaction?: {
      id: string;
      amount: number;
      status: string;
    };
  } | null>(null);
  
  const [recipientId, setRecipientId] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [biometricVerified, setBiometricVerified] = useState(false);

  const simulateBiometricVerify = () => {
    setLoading(true);
    setTimeout(() => {
      setBiometricVerified(true);
      setLoading(false);
    }, 1500);
  };

  const validatePayment = () => {
    if (!recipientId.trim()) {
      setError("Recipient ID is required");
      return false;
    }
    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setError("Please enter a valid amount");
      return false;
    }
    if (amountNum > user.walletBalance) {
      setError(`Insufficient balance. Available: $${user.walletBalance.toFixed(2)}`);
      return false;
    }
    return true;
  };

  const handleProceedToVerify = () => {
    if (validatePayment()) {
      setStep("verify");
    }
  };

  const handleConfirmPayment = async () => {
    if (!biometricVerified) {
      setError("Please verify your identity");
      return;
    }

    setStep("processing");
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/pay", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fromUserId: user.id,
          toUserId: recipientId,
          cardId: card.id,
          amount: parseFloat(amount),
          description: description || undefined,
          isOffline,
        }),
      });

      const data = await response.json();
      
      setResult({
        success: data.success,
        message: data.message,
        fraudAlert: data.fraudAlert,
        transaction: data.transaction,
      });
      setStep("result");
    } catch {
      setResult({
        success: false,
        message: "Network error. Please try again.",
      });
      setStep("result");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full p-1 hover:bg-muted"
        >
          <X className="h-5 w-5 text-muted-foreground" />
        </button>

        {/* Step: Payment Details */}
        {step === "details" && (
          <div className="space-y-4">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-foreground">Send Payment</h2>
              <p className="text-sm text-muted-foreground">
                {isOffline 
                  ? "Payment will be queued for offline processing" 
                  : "Enter payment details below"
                }
              </p>
            </div>

            {isOffline && (
              <div className="mb-4 flex items-center gap-2 rounded-lg bg-accent/10 p-3">
                <Clock className="h-4 w-4 text-accent" />
                <p className="text-sm text-accent">Offline mode - transaction will sync later</p>
              </div>
            )}

            {error && (
              <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Recipient User ID
              </label>
              <Input
                value={recipientId}
                onChange={(e) => { setRecipientId(e.target.value); setError(""); }}
                placeholder="usr_recipient123"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Enter the recipients user ID
              </p>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Amount (USD)
              </label>
              <Input
                type="number"
                value={amount}
                onChange={(e) => { setAmount(e.target.value); setError(""); }}
                placeholder="0.00"
                min="0.01"
                step="0.01"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Available balance: ${user.walletBalance.toFixed(2)}
              </p>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">
                Description (Optional)
              </label>
              <Input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Payment for..."
              />
            </div>

            <div className="flex gap-2 pt-2">
              <Button variant="outline" onClick={onClose} className="flex-1">
                Cancel
              </Button>
              <Button onClick={handleProceedToVerify} className="flex-1">
                Continue
              </Button>
            </div>
          </div>
        )}

        {/* Step: Verify Identity */}
        {step === "verify" && (
          <div className="space-y-4">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-foreground">Verify Identity</h2>
              <p className="text-sm text-muted-foreground">
                Confirm your identity to authorize this payment
              </p>
            </div>

            {/* Payment Summary */}
            <div className="rounded-lg border border-border bg-muted/30 p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Amount</span>
                <span className="text-lg font-bold text-foreground">${parseFloat(amount).toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">To</span>
                <span className="font-mono text-sm text-foreground">{recipientId}</span>
              </div>
              {description && (
                <div className="mt-2 border-t border-border pt-2">
                  <span className="text-xs text-muted-foreground">{description}</span>
                </div>
              )}
            </div>

            {error && (
              <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {/* Biometric Verification */}
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
                    {loading ? "Verifying..." : "Verify with biometric to authorize"}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={simulateBiometricVerify}
                    disabled={loading}
                  >
                    {loading ? "Verifying..." : "Verify Identity"}
                  </Button>
                </>
              ) : (
                <>
                  <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                    <Check className="h-8 w-8 text-primary" />
                  </div>
                  <p className="text-sm font-medium text-primary">Identity Verified</p>
                </>
              )}
            </div>

            <div className="flex gap-2 pt-2">
              <Button variant="outline" onClick={() => setStep("details")} className="flex-1">
                Back
              </Button>
              <Button 
                onClick={handleConfirmPayment} 
                className="flex-1"
                disabled={!biometricVerified}
              >
                <Send className="mr-2 h-4 w-4" />
                Confirm Payment
              </Button>
            </div>
          </div>
        )}

        {/* Step: Processing */}
        {step === "processing" && (
          <div className="flex flex-col items-center py-8">
            <Loader2 className="mb-4 h-12 w-12 animate-spin text-primary" />
            <h2 className="mb-2 text-xl font-semibold text-foreground">Processing Payment</h2>
            <p className="text-sm text-muted-foreground">
              Running fraud detection and processing transaction...
            </p>
          </div>
        )}

        {/* Step: Result */}
        {step === "result" && result && (
          <div className="space-y-4">
            <div className="flex flex-col items-center py-4">
              {result.success ? (
                <>
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                    <CheckCircle className="h-10 w-10 text-primary" />
                  </div>
                  <h2 className="mb-2 text-xl font-semibold text-foreground">
                    {isOffline ? "Payment Queued" : "Payment Successful"}
                  </h2>
                </>
              ) : (
                <>
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
                    <X className="h-10 w-10 text-destructive" />
                  </div>
                  <h2 className="mb-2 text-xl font-semibold text-foreground">Payment Failed</h2>
                </>
              )}
              <p className="text-center text-sm text-muted-foreground">{result.message}</p>
            </div>

            {result.fraudAlert && (
              <div className="flex items-center gap-2 rounded-lg bg-accent/10 p-3">
                <AlertTriangle className="h-4 w-4 text-accent" />
                <p className="text-sm text-accent">
                  This transaction was flagged by our fraud detection system
                </p>
              </div>
            )}

            {result.transaction && (
              <div className="rounded-lg border border-border bg-muted/30 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Transaction ID</span>
                  <span className="font-mono text-xs text-foreground">{result.transaction.id}</span>
                </div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Amount</span>
                  <span className="font-semibold text-foreground">${result.transaction.amount.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Status</span>
                  <span className={`rounded px-2 py-0.5 text-xs font-medium capitalize ${
                    result.transaction.status === "completed" ? "bg-primary/10 text-primary" :
                    result.transaction.status === "offline_queued" ? "bg-accent/10 text-accent" :
                    "bg-destructive/10 text-destructive"
                  }`}>
                    {result.transaction.status.replace("_", " ")}
                  </span>
                </div>
              </div>
            )}

            <div className="rounded-lg bg-muted/50 p-3">
              <div className="flex items-start gap-2">
                <Shield className="mt-0.5 h-4 w-4 text-primary" />
                <p className="text-xs text-muted-foreground">
                  This transaction was verified with biometric authentication and analyzed by our AI fraud detection system.
                </p>
              </div>
            </div>

            <Button onClick={onComplete} className="w-full">
              Done
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
