// GET /api/transactions - Get Transaction History

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const userId = request.nextUrl.searchParams.get('userId');
    const limit = parseInt(request.nextUrl.searchParams.get('limit') || '50');
    const offset = parseInt(request.nextUrl.searchParams.get('offset') || '0');

    let transactions;
    
    if (userId) {
      transactions = db.getTransactionsByUserId(userId);
    } else {
      transactions = db.getAllTransactions();
    }

    // Sort by date descending
    transactions.sort((a, b) => 
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );

    // Paginate
    const paginatedTransactions = transactions.slice(offset, offset + limit);

    // Calculate stats
    const stats = {
      total: transactions.length,
      completed: transactions.filter(t => t.status === 'completed').length,
      failed: transactions.filter(t => t.status === 'failed').length,
      pending: transactions.filter(t => t.status === 'pending').length,
      offlineQueued: transactions.filter(t => t.status === 'offline_queued').length,
      totalVolume: transactions
        .filter(t => t.status === 'completed')
        .reduce((sum, t) => sum + t.amount, 0)
    };

    return NextResponse.json({
      success: true,
      transactions: paginatedTransactions,
      pagination: {
        total: transactions.length,
        limit,
        offset,
        hasMore: offset + limit < transactions.length
      },
      stats
    }, { status: 200 });

  } catch (error) {
    console.error('Get transactions error:', error);
    return NextResponse.json({
      success: false,
      message: 'Internal server error'
    }, { status: 500 });
  }
}
