"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  CreditCard, 
  Plus, 
  Send, 
  RefreshCw, 
  Shield, 
  Clock, 
  CheckCircle, 
  XCircle,
  AlertTriangle,
  Loader2,
  Wallet,
  ArrowUpRight,
  ArrowDownLeft
} from "lucide-react";
import { PaymentModal } from "./payment-modal";
import { VirtualCardDisplay } from "./virtual-card-display";
import type { DemoUser, DemoCard } from "@/app/demo/page";

interface Transaction {
  id: string;
  fromUserId: string;
  toUserId: string;
  amount: number;
  status: string;
  type: string;
  fraudScore: number;
  createdAt: string;
  description?: string;
}

interface OfflineTransaction {
  id: string;
  transaction: {
    amount: number;
    toUserId: string;
  };
  syncStatus: string;
  queuedAt: string;
}

interface DashboardProps {
  user: DemoUser;
  card: DemoCard | null;
  token: string;
  isOffline: boolean;
  onCardCreated: (card: DemoCard) => void;
  onUserUpdate: (user: DemoUser) => void;
}

export function Dashboard({ 
  user, 
  card, 
  token, 
  isOffline, 
  onCardCreated,
  onUserUpdate 
}: DashboardProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [offlineQueue, setOfflineQueue] = useState<OfflineTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [cardLoading, setCardLoading] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      // Fetch transactions
      const txResponse = await fetch(`/api/transactions?userId=${user.id}`);
      const txData = await txResponse.json();
      if (txData.success) {
        setTransactions(txData.transactions);
      }

      // Fetch offline queue
      const queueResponse = await fetch(`/api/sync?userId=${user.id}`);
      const queueData = await queueResponse.json();
      if (queueData.success) {
        setOfflineQueue(queueData.queue);
      }

      // Fetch updated user data
      const userResponse = await fetch(`/api/users/${user.id}`);
      const userData = await userResponse.json();
      if (userData.success) {
        onUserUpdate(userData.user);
      }
    } catch (error) {
      console.error("Failed to fetch data:", error);
    }
  }, [user.id, onUserUpdate]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateCard = async () => {
    setCardLoading(true);
    try {
      const response = await fetch("/api/create-card", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          userId: user.id,
          dailyLimit: 5000
        }),
      });

      const data = await response.json();
      if (data.success && data.card) {
        onCardCreated(data.card);
      }
    } catch (error) {
      console.error("Failed to create card:", error);
    } finally {
      setCardLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncLoading(true);
    try {
      const response = await fetch("/api/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: user.id }),
      });

      const data = await response.json();
      if (data.success) {
        await fetchData();
      }
    } catch (error) {
      console.error("Sync failed:", error);
    } finally {
      setSyncLoading(false);
    }
  };

  const handlePaymentComplete = () => {
    setShowPaymentModal(false);
    fetchData();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-primary" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-destructive" />;
      case "offline_queued":
        return <Clock className="h-4 w-4 text-accent" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Wallet Balance</p>
                <p className="text-2xl font-bold text-foreground">${user.walletBalance.toFixed(2)}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                <Wallet className="h-5 w-5 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">KYC Status</p>
                <p className="text-lg font-semibold capitalize text-primary">{user.kycStatus}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                <Shield className="h-5 w-5 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Transactions</p>
                <p className="text-2xl font-bold text-foreground">{transactions.length}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10">
                <ArrowUpRight className="h-5 w-5 text-accent" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Offline Queue</p>
                <p className="text-2xl font-bold text-foreground">{offlineQueue.length}</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
                <Clock className="h-5 w-5 text-muted-foreground" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Virtual Card Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-primary" />
              Virtual Card
            </CardTitle>
            <CardDescription>
              {card ? "Your tokenized payment card" : "Create a virtual card to make payments"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {card ? (
              <VirtualCardDisplay card={card} userId={user.id} />
            ) : (
              <div className="flex flex-col items-center rounded-lg border-2 border-dashed border-border bg-muted/30 p-8">
                <CreditCard className="mb-4 h-12 w-12 text-muted-foreground" />
                <p className="mb-4 text-center text-muted-foreground">
                  You dont have a virtual card yet. Create one to start making payments.
                </p>
                <Button onClick={handleCreateCard} disabled={cardLoading}>
                  {cardLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="mr-2 h-4 w-4" />
                      Create Virtual Card
                    </>
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              {isOffline 
                ? "Offline mode - transactions will be queued" 
                : "Send and receive payments instantly"
              }
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button 
              className="w-full justify-start" 
              size="lg"
              onClick={() => setShowPaymentModal(true)}
              disabled={!card}
            >
              <Send className="mr-3 h-5 w-5" />
              Send Payment
              {isOffline && (
                <span className="ml-auto rounded bg-accent/20 px-2 py-0.5 text-xs text-accent">
                  Offline
                </span>
              )}
            </Button>

            {offlineQueue.length > 0 && !isOffline && (
              <Button 
                variant="outline" 
                className="w-full justify-start" 
                size="lg"
                onClick={handleSync}
                disabled={syncLoading}
              >
                {syncLoading ? (
                  <Loader2 className="mr-3 h-5 w-5 animate-spin" />
                ) : (
                  <RefreshCw className="mr-3 h-5 w-5" />
                )}
                Sync Offline Transactions
                <span className="ml-auto rounded bg-accent/20 px-2 py-0.5 text-xs text-accent">
                  {offlineQueue.length}
                </span>
              </Button>
            )}

            <Button 
              variant="outline" 
              className="w-full justify-start" 
              size="lg"
              onClick={fetchData}
              disabled={loading}
            >
              {loading ? (
                <Loader2 className="mr-3 h-5 w-5 animate-spin" />
              ) : (
                <RefreshCw className="mr-3 h-5 w-5" />
              )}
              Refresh Data
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Offline Queue */}
      {offlineQueue.length > 0 && (
        <Card className="border-accent/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-accent">
              <Clock className="h-5 w-5" />
              Offline Transaction Queue
            </CardTitle>
            <CardDescription>
              These transactions will be processed when you sync
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {offlineQueue.map((tx) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between rounded-lg border border-border bg-card p-3"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10">
                      <Clock className="h-4 w-4 text-accent" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        Payment - ${tx.transaction.amount.toFixed(2)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Queued {new Date(tx.queuedAt).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                  <span className="rounded bg-accent/20 px-2 py-1 text-xs text-accent">
                    {tx.syncStatus}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Transaction History */}
      <Card>
        <CardHeader>
          <CardTitle>Transaction History</CardTitle>
          <CardDescription>
            Your recent transactions and their status
          </CardDescription>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center">
              <ArrowUpRight className="mb-3 h-10 w-10 text-muted-foreground" />
              <p className="text-muted-foreground">No transactions yet</p>
              <p className="text-sm text-muted-foreground">
                Make your first payment to see it here
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {transactions.slice(0, 10).map((tx) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between rounded-lg border border-border bg-card p-3"
                >
                  <div className="flex items-center gap-3">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
                      tx.fromUserId === user.id 
                        ? "bg-destructive/10" 
                        : "bg-primary/10"
                    }`}>
                      {tx.fromUserId === user.id ? (
                        <ArrowUpRight className="h-4 w-4 text-destructive" />
                      ) : (
                        <ArrowDownLeft className="h-4 w-4 text-primary" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {tx.fromUserId === user.id ? "Sent" : "Received"} ${tx.amount.toFixed(2)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(tx.createdAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {tx.fraudScore > 30 && (
                      <AlertTriangle
                        className="h-4 w-4 text-accent"
                        aria-label={`Fraud score: ${tx.fraudScore}`}
                      />
                    )}
                    {getStatusIcon(tx.status)}
                    <span className={`text-xs capitalize ${
                      tx.status === "completed" ? "text-primary" :
                      tx.status === "failed" ? "text-destructive" : "text-muted-foreground"
                    }`}>
                      {tx.status.replace("_", " ")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payment Modal */}
      {showPaymentModal && card && (
        <PaymentModal
          user={user}
          card={card}
          isOffline={isOffline}
          onClose={() => setShowPaymentModal(false)}
          onComplete={handlePaymentComplete}
        />
      )}
    </div>
  );
}
