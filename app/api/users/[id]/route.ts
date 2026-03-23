// GET /api/users/[id] - Get User Details

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    const { id } = await params;
    
    const user = db.getUserById(id);
    if (!user) {
      return NextResponse.json({
        success: false,
        message: 'User not found'
      }, { status: 404 });
    }

    // Get user's cards
    const cards = db.getCardsByUserId(id);
    
    // Get user's transactions
    const transactions = db.getTransactionsByUserId(id);
    
    // Get offline queue
    const offlineQueue = db.getOfflineQueueByUserId(id);

    return NextResponse.json({
      success: true,
      user: {
        id: user.id,
        fullName: user.fullName,
        phone: user.phone,
        nationalId: user.nationalId,
        email: user.email,
        createdAt: user.createdAt,
        kycStatus: user.kycStatus,
        walletBalance: user.walletBalance
      },
      cards: cards.map(card => ({
        id: card.id,
        lastFourDigits: card.lastFourDigits,
        expiryDate: card.expiryDate,
        status: card.status,
        dailyLimit: card.dailyLimit,
        spentToday: card.spentToday,
        createdAt: card.createdAt
      })),
      recentTransactions: transactions.slice(-10).reverse(),
      offlineQueueCount: offlineQueue.length,
      stats: {
        totalTransactions: transactions.length,
        completedTransactions: transactions.filter(t => t.status === 'completed').length,
        totalSpent: transactions
          .filter(t => t.fromUserId === id && t.status === 'completed')
          .reduce((sum, t) => sum + t.amount, 0),
        totalReceived: transactions
          .filter(t => t.toUserId === id && t.status === 'completed')
          .reduce((sum, t) => sum + t.amount, 0)
      }
    }, { status: 200 });

  } catch (error) {
    console.error('Get user error:', error);
    return NextResponse.json({
      success: false,
      message: 'Internal server error'
    }, { status: 500 });
  }
}
