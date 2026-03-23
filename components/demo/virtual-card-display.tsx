"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Eye, EyeOff, RefreshCw, Shield, Loader2 } from "lucide-react";
import type { DemoCard } from "@/app/demo/page";

interface VirtualCardDisplayProps {
  card: DemoCard;
  userId: string;
}

export function VirtualCardDisplay({ card, userId }: VirtualCardDisplayProps) {
  const [showCvv, setShowCvv] = useState(false);
  const [cvv, setCvv] = useState("***");
  const [cvvLoading, setCvvLoading] = useState(false);
  const [cvvExpiry, setCvvExpiry] = useState<Date | null>(null);
  const [timeLeft, setTimeLeft] = useState(30);

  const fetchCvv = useCallback(async () => {
    setCvvLoading(true);
    try {
      const response = await fetch(`/api/cards/${card.id}/cvv`);
      const data = await response.json();
      if (data.success) {
        setCvv(data.cvv);
        setCvvExpiry(new Date(data.validUntil));
      }
    } catch (error) {
      console.error("Failed to fetch CVV:", error);
    } finally {
      setCvvLoading(false);
    }
  }, [card.id]);

  useEffect(() => {
    if (showCvv) {
      fetchCvv();
    }
  }, [showCvv, fetchCvv]);

  useEffect(() => {
    if (!cvvExpiry) return;

    const interval = setInterval(() => {
      const now = new Date();
      const remaining = Math.max(0, Math.ceil((cvvExpiry.getTime() - now.getTime()) / 1000));
      setTimeLeft(remaining);

      if (remaining === 0) {
        fetchCvv();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [cvvExpiry, fetchCvv]);

  return (
    <div className="space-y-4">
      {/* Card Visual */}
      <div className="relative aspect-[1.586/1] overflow-hidden rounded-xl bg-gradient-to-br from-primary via-primary/80 to-primary/60 p-6 text-primary-foreground shadow-lg">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute left-1/4 top-1/4 h-32 w-32 rounded-full bg-foreground" />
          <div className="absolute right-1/4 bottom-1/4 h-24 w-24 rounded-full bg-foreground" />
        </div>

        <div className="relative flex h-full flex-col justify-between">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              <span className="text-sm font-medium">AfriCard</span>
            </div>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              card.status === "active" 
                ? "bg-foreground/20" 
                : "bg-destructive/50"
            }`}>
              {card.status}
            </span>
          </div>

          {/* Chip */}
          <div className="flex items-center gap-4">
            <div className="h-10 w-12 rounded bg-accent/80" />
            <div className="h-6 w-8 rounded-full border-2 border-foreground/30" />
          </div>

          {/* Card Number */}
          <div>
            <p className="mb-1 text-xs opacity-70">Card Number</p>
            <p className="font-mono text-lg tracking-wider">
              **** **** **** {card.lastFourDigits}
            </p>
          </div>

          {/* Bottom Row */}
          <div className="flex items-end justify-between">
            <div>
              <p className="text-xs opacity-70">User ID</p>
              <p className="font-mono text-sm">{userId.slice(0, 12)}...</p>
            </div>
            <div className="text-right">
              <p className="text-xs opacity-70">Expires</p>
              <p className="font-mono text-sm">{card.expiryDate}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Card Details */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-border bg-muted/30 p-3">
          <p className="mb-1 text-xs text-muted-foreground">Daily Limit</p>
          <p className="font-semibold text-foreground">${card.dailyLimit.toFixed(2)}</p>
        </div>
        <div className="rounded-lg border border-border bg-muted/30 p-3">
          <p className="mb-1 text-xs text-muted-foreground">Spent Today</p>
          <p className="font-semibold text-foreground">${card.spentToday.toFixed(2)}</p>
        </div>
      </div>

      {/* Dynamic CVV */}
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h4 className="text-sm font-medium text-foreground">Dynamic CVV</h4>
            <p className="text-xs text-muted-foreground">Changes every 30 seconds</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowCvv(!showCvv)}
          >
            {showCvv ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
          </Button>
        </div>

        {showCvv && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded bg-muted px-4 py-2">
                {cvvLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  <span className="font-mono text-xl font-bold text-foreground">{cvv}</span>
                )}
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={fetchCvv}
                disabled={cvvLoading}
              >
                <RefreshCw className={`h-4 w-4 ${cvvLoading ? "animate-spin" : ""}`} />
              </Button>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Expires in</p>
              <p className={`font-mono text-lg font-bold ${
                timeLeft <= 5 ? "text-destructive" : "text-foreground"
              }`}>
                {timeLeft}s
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Security Info */}
      <div className="rounded-lg bg-primary/5 p-3">
        <div className="flex items-start gap-2">
          <Shield className="mt-0.5 h-4 w-4 text-primary" />
          <div>
            <p className="text-sm font-medium text-foreground">Tokenized Security</p>
            <p className="text-xs text-muted-foreground">
              Your card number is tokenized and never stored in plain text. 
              The dynamic CVV provides additional protection against fraud.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
