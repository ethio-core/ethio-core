// POST /api/sync - Sync Offline Transactions

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';
import { generateId } from '@/lib/crypto';
import { analyzeTransaction } from '@/lib/fraud-detection';
import type { Transaction } from '@/lib/types';

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body = await request.json();
    const { userId } = body;

    if (!userId) {
      return NextResponse.json({
        success: false,
        message: 'Missing required field: userId'
      }, { status: 400 });
    }

    // Get offline queue for user
    const offlineQueue = db.getOfflineQueueByUserId(userId);
    
    if (offlineQueue.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No offline transactions to sync',
        synced: 0,
        failed: 0
      }, { status: 200 });
    }

    const results = {
      synced: 0,
      failed: 0,
      transactions: [] as Transaction[],
      errors: [] as { id: string; reason: string }[]
    };

    // Process each queued transaction
    for (const offlineTx of offlineQueue) {
      try {
        // Mark as syncing
        db.updateOfflineTransaction(offlineTx.id, { syncStatus: 'syncing' });

        const { transaction: txData } = offlineTx;
        
        // Get sender and receiver
        const sender = db.getUserById(txData.fromUserId);
        const receiver = db.getUserById(txData.toUserId);
        const card = db.getCardById(txData.fromCardId);

        if (!sender || !receiver || !card) {
          db.updateOfflineTransaction(offlineTx.id, { 
            syncStatus: 'failed',
            retryCount: offlineTx.retryCount + 1
          });
          results.failed++;
          results.errors.push({ 
            id: offlineTx.id, 
            reason: 'User or card not found' 
          });
          continue;
        }

        // Check balance
        if (sender.walletBalance < txData.amount) {
          db.updateOfflineTransaction(offlineTx.id, { 
            syncStatus: 'failed',
            retryCount: offlineTx.retryCount + 1
          });
          results.failed++;
          results.errors.push({ 
            id: offlineTx.id, 
            reason: 'Insufficient balance' 
          });
          continue;
        }

        // Run fraud check
        const recentTransactions = db.getTransactionsByUserId(txData.fromUserId);
        const fraudResult = analyzeTransaction(
          { amount: txData.amount, type: 'payment', fromUserId: txData.fromUserId, toUserId: txData.toUserId },
          sender,
          card,
          recentTransactions
        );

        if (fraudResult.blocked) {
          db.updateOfflineTransaction(offlineTx.id, { 
            syncStatus: 'failed',
            retryCount: offlineTx.retryCount + 1
          });
          results.failed++;
          results.errors.push({ 
            id: offlineTx.id, 
            reason: `Blocked by fraud detection: ${fraudResult.reasons.join(', ')}` 
          });
          continue;
        }

        // Process transaction
        const transaction: Transaction = {
          id: generateId('tx'),
          ...txData,
          status: 'completed',
          syncedAt: new Date().toISOString()
        };

        // Update balances
        db.updateUser(txData.fromUserId, { 
          walletBalance: sender.walletBalance - txData.amount 
        });
        db.updateUser(txData.toUserId, { 
          walletBalance: receiver.walletBalance + txData.amount 
        });

        // Update card daily spend
        db.updateCard(txData.fromCardId, { 
          spentToday: card.spentToday + txData.amount 
        });

        // Save transaction
        db.createTransaction(transaction);

        // Remove from offline queue
        db.removeOfflineTransaction(offlineTx.id);

        results.synced++;
        results.transactions.push(transaction);

      } catch {
        db.updateOfflineTransaction(offlineTx.id, { 
          syncStatus: 'failed',
          retryCount: offlineTx.retryCount + 1
        });
        results.failed++;
        results.errors.push({ 
          id: offlineTx.id, 
          reason: 'Processing error' 
        });
      }
    }

    return NextResponse.json({
      success: true,
      message: `Sync complete: ${results.synced} synced, ${results.failed} failed`,
      ...results
    }, { status: 200 });

  } catch (error) {
    console.error('Sync error:', error);
    return NextResponse.json({
      success: false,
      message: 'Internal server error during sync'
    }, { status: 500 });
  }
}

// GET /api/sync - Get offline queue status
export async function GET(request: NextRequest): Promise<NextResponse> {
  const userId = request.nextUrl.searchParams.get('userId');
  
  if (!userId) {
    return NextResponse.json({
      success: false,
      message: 'Missing query parameter: userId'
    }, { status: 400 });
  }

  const offlineQueue = db.getOfflineQueueByUserId(userId);
  
  return NextResponse.json({
    success: true,
    queueLength: offlineQueue.length,
    queue: offlineQueue,
    totalAmount: offlineQueue.reduce((sum, tx) => sum + tx.transaction.amount, 0)
  }, { status: 200 });
}
