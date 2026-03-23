// POST /api/pay - Process Payment Transaction

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';
import { generateId } from '@/lib/crypto';
import { analyzeTransaction } from '@/lib/fraud-detection';
import type { Transaction, OfflineTransaction, PaymentRequest, PaymentResponse } from '@/lib/types';

export async function POST(request: NextRequest): Promise<NextResponse<PaymentResponse>> {
  try {
    const body: PaymentRequest = await request.json();
    const { fromUserId, toUserId, cardId, amount, description, isOffline } = body;

    // Validate required fields
    if (!fromUserId || !toUserId || !cardId || !amount) {
      return NextResponse.json({
        success: false,
        message: 'Missing required fields: fromUserId, toUserId, cardId, amount'
      }, { status: 400 });
    }

    // Validate amount
    if (amount <= 0) {
      return NextResponse.json({
        success: false,
        message: 'Amount must be greater than 0'
      }, { status: 400 });
    }

    // Get sender
    const sender = db.getUserById(fromUserId);
    if (!sender) {
      return NextResponse.json({
        success: false,
        message: 'Sender not found'
      }, { status: 404 });
    }

    // Get receiver
    const receiver = db.getUserById(toUserId);
    if (!receiver) {
      return NextResponse.json({
        success: false,
        message: 'Receiver not found'
      }, { status: 404 });
    }

    // Get card
    const card = db.getCardById(cardId);
    if (!card) {
      return NextResponse.json({
        success: false,
        message: 'Card not found'
      }, { status: 404 });
    }

    // Verify card ownership
    if (card.userId !== fromUserId) {
      return NextResponse.json({
        success: false,
        message: 'Card does not belong to sender'
      }, { status: 403 });
    }

    // Check balance
    if (sender.walletBalance < amount) {
      return NextResponse.json({
        success: false,
        message: `Insufficient balance. Available: $${sender.walletBalance}, Required: $${amount}`
      }, { status: 400 });
    }

    // Get recent transactions for fraud analysis
    const recentTransactions = db.getTransactionsByUserId(fromUserId);

    // Run fraud detection
    const fraudResult = analyzeTransaction(
      { amount, type: 'payment', fromUserId, toUserId },
      sender,
      card,
      recentTransactions
    );

    // Handle offline mode
    if (isOffline) {
      const offlineTx: OfflineTransaction = {
        id: generateId('offline'),
        transaction: {
          fromUserId,
          toUserId,
          fromCardId: cardId,
          amount,
          currency: 'USD',
          type: 'payment',
          fraudScore: fraudResult.score,
          createdAt: new Date().toISOString(),
          description
        },
        queuedAt: new Date().toISOString(),
        syncStatus: 'queued',
        retryCount: 0
      };

      db.queueOfflineTransaction(offlineTx);

      return NextResponse.json({
        success: true,
        transaction: {
          id: offlineTx.id,
          fromUserId,
          toUserId,
          fromCardId: cardId,
          amount,
          currency: 'USD',
          status: 'offline_queued',
          type: 'payment',
          fraudScore: fraudResult.score,
          createdAt: offlineTx.queuedAt,
          description
        },
        message: 'Transaction queued for offline processing. Will sync when connection is restored.',
        fraudAlert: fraudResult.riskLevel !== 'low'
      }, { status: 202 });
    }

    // Block high fraud score transactions
    if (fraudResult.blocked) {
      const blockedTx: Transaction = {
        id: generateId('tx'),
        fromUserId,
        toUserId,
        fromCardId: cardId,
        amount,
        currency: 'USD',
        status: 'failed',
        type: 'payment',
        fraudScore: fraudResult.score,
        createdAt: new Date().toISOString(),
        description
      };

      db.createTransaction(blockedTx);

      return NextResponse.json({
        success: false,
        transaction: blockedTx,
        message: `Transaction blocked by fraud detection. Risk level: ${fraudResult.riskLevel}. Reasons: ${fraudResult.reasons.join(', ')}`,
        fraudAlert: true
      }, { status: 403 });
    }

    // Process transaction
    const transaction: Transaction = {
      id: generateId('tx'),
      fromUserId,
      toUserId,
      fromCardId: cardId,
      amount,
      currency: 'USD',
      status: 'completed',
      type: 'payment',
      fraudScore: fraudResult.score,
      createdAt: new Date().toISOString(),
      description
    };

    // Update balances
    db.updateUser(fromUserId, { 
      walletBalance: sender.walletBalance - amount 
    });
    db.updateUser(toUserId, { 
      walletBalance: receiver.walletBalance + amount 
    });

    // Update card daily spend
    db.updateCard(cardId, { 
      spentToday: card.spentToday + amount 
    });

    // Save transaction
    db.createTransaction(transaction);

    return NextResponse.json({
      success: true,
      transaction,
      message: `Payment of $${amount} completed successfully`,
      fraudAlert: fraudResult.riskLevel !== 'low',
      details: {
        newSenderBalance: sender.walletBalance - amount,
        fraudRiskLevel: fraudResult.riskLevel,
        fraudScore: fraudResult.score
      }
    }, { status: 200 });

  } catch (error) {
    console.error('Payment error:', error);
    return NextResponse.json({
      success: false,
      message: 'Internal server error during payment'
    }, { status: 500 });
  }
}

// GET /api/pay - Get payment requirements
export async function GET(): Promise<NextResponse> {
  return NextResponse.json({
    requirements: {
      fromUserId: 'string (required) - Sender user ID',
      toUserId: 'string (required) - Receiver user ID',
      cardId: 'string (required) - Card ID to use for payment',
      amount: 'number (required) - Amount to transfer',
      description: 'string (optional) - Transaction description',
      isOffline: 'boolean (optional) - Queue for offline processing'
    },
    example: {
      fromUserId: 'usr_sender123',
      toUserId: 'usr_receiver456',
      cardId: 'card_abc123',
      amount: 50.00,
      description: 'Payment for groceries'
    },
    fraudProtection: [
      'Real-time fraud scoring',
      'Velocity checks (hourly/daily limits)',
      'Daily spending limits',
      'New account risk assessment',
      'Suspicious pattern detection'
    ]
  });
}
