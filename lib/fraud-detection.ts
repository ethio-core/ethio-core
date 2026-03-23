// AI-powered fraud detection (simulated for MVP)

import type { Transaction, User, VirtualCard } from './types';

export interface FraudCheckResult {
  score: number; // 0-100, higher = more suspicious
  blocked: boolean;
  reasons: string[];
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

// Transaction limits and thresholds
const FRAUD_THRESHOLDS = {
  singleTransactionLimit: 10000, // Block transactions over this amount
  dailyVelocityLimit: 5, // Max transactions per day
  hourlyVelocityLimit: 3, // Max transactions per hour
  suspiciousAmountThreshold: 5000, // Flag large transactions
  newAccountAgeLimit: 24 * 60 * 60 * 1000, // 24 hours in ms
  blockScore: 70, // Block if fraud score >= this
};

// Analyze transaction for fraud signals
export function analyzeTransaction(
  transaction: Pick<Transaction, 'amount' | 'type' | 'fromUserId' | 'toUserId'>,
  user: User,
  card: VirtualCard,
  recentTransactions: Transaction[]
): FraudCheckResult {
  const reasons: string[] = [];
  let score = 0;

  // 1. Check transaction amount
  if (transaction.amount > FRAUD_THRESHOLDS.singleTransactionLimit) {
    score += 40;
    reasons.push(`Amount exceeds limit: $${transaction.amount} > $${FRAUD_THRESHOLDS.singleTransactionLimit}`);
  } else if (transaction.amount > FRAUD_THRESHOLDS.suspiciousAmountThreshold) {
    score += 15;
    reasons.push(`Large transaction amount: $${transaction.amount}`);
  }

  // 2. Check daily spending limit
  if (card.spentToday + transaction.amount > card.dailyLimit) {
    score += 30;
    reasons.push(`Would exceed daily limit: $${card.spentToday + transaction.amount} > $${card.dailyLimit}`);
  }

  // 3. Velocity check - transactions in last hour
  const oneHourAgo = Date.now() - 60 * 60 * 1000;
  const recentHourTransactions = recentTransactions.filter(
    t => new Date(t.createdAt).getTime() > oneHourAgo
  );
  if (recentHourTransactions.length >= FRAUD_THRESHOLDS.hourlyVelocityLimit) {
    score += 25;
    reasons.push(`High velocity: ${recentHourTransactions.length} transactions in last hour`);
  }

  // 4. Velocity check - transactions today
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const todayTransactions = recentTransactions.filter(
    t => new Date(t.createdAt).getTime() > todayStart.getTime()
  );
  if (todayTransactions.length >= FRAUD_THRESHOLDS.dailyVelocityLimit) {
    score += 20;
    reasons.push(`High daily velocity: ${todayTransactions.length} transactions today`);
  }

  // 5. New account risk
  const accountAge = Date.now() - new Date(user.createdAt).getTime();
  if (accountAge < FRAUD_THRESHOLDS.newAccountAgeLimit) {
    score += 15;
    reasons.push('New account (less than 24 hours old)');
  }

  // 6. Self-transfer check
  if (transaction.fromUserId === transaction.toUserId) {
    score += 10;
    reasons.push('Self-transfer detected');
  }

  // 7. Round number check (common in fraud)
  if (transaction.amount % 100 === 0 && transaction.amount >= 1000) {
    score += 5;
    reasons.push('Suspiciously round amount');
  }

  // 8. KYC status check
  if (user.kycStatus !== 'verified') {
    score += 20;
    reasons.push(`KYC not verified: ${user.kycStatus}`);
  }

  // 9. Card status check
  if (card.status !== 'active') {
    score += 50;
    reasons.push(`Card not active: ${card.status}`);
  }

  // Determine risk level
  let riskLevel: FraudCheckResult['riskLevel'];
  if (score >= 70) riskLevel = 'critical';
  else if (score >= 50) riskLevel = 'high';
  else if (score >= 30) riskLevel = 'medium';
  else riskLevel = 'low';

  return {
    score: Math.min(score, 100),
    blocked: score >= FRAUD_THRESHOLDS.blockScore,
    reasons,
    riskLevel
  };
}

// Check for suspicious patterns (behavioral analysis)
export function analyzeUserBehavior(
  user: User,
  transactions: Transaction[]
): {
  riskScore: number;
  anomalies: string[];
} {
  const anomalies: string[] = [];
  let riskScore = 0;

  // Check for unusual transaction patterns
  const amounts = transactions.map(t => t.amount);
  const avgAmount = amounts.reduce((a, b) => a + b, 0) / amounts.length || 0;
  const maxAmount = Math.max(...amounts, 0);

  // Flag if recent transaction is 3x average
  if (maxAmount > avgAmount * 3 && amounts.length > 5) {
    riskScore += 15;
    anomalies.push('Unusual transaction size detected');
  }

  // Check transaction frequency changes
  const recentWeek = transactions.filter(
    t => Date.now() - new Date(t.createdAt).getTime() < 7 * 24 * 60 * 60 * 1000
  );
  const previousWeek = transactions.filter(
    t => {
      const age = Date.now() - new Date(t.createdAt).getTime();
      return age >= 7 * 24 * 60 * 60 * 1000 && age < 14 * 24 * 60 * 60 * 1000;
    }
  );

  if (recentWeek.length > previousWeek.length * 2 && previousWeek.length > 0) {
    riskScore += 10;
    anomalies.push('Significant increase in transaction frequency');
  }

  return { riskScore, anomalies };
}
