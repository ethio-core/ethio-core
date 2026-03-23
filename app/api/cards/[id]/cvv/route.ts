// GET /api/cards/[id]/cvv - Get Dynamic CVV

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';
import { generateDynamicCvv } from '@/lib/crypto';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    const { id } = await params;
    
    const card = db.getCardById(id);
    if (!card) {
      return NextResponse.json({
        success: false,
        message: 'Card not found'
      }, { status: 404 });
    }

    if (card.status !== 'active') {
      return NextResponse.json({
        success: false,
        message: `Card is ${card.status}`
      }, { status: 403 });
    }

    // Generate dynamic CVV
    const cvv = generateDynamicCvv(card.cvvSeed);
    const validUntil = new Date();
    validUntil.setSeconds(validUntil.getSeconds() + 30); // Valid for 30 seconds

    return NextResponse.json({
      success: true,
      cvv,
      validUntil: validUntil.toISOString(),
      message: 'CVV changes every 30 seconds'
    }, { status: 200 });

  } catch (error) {
    console.error('Get CVV error:', error);
    return NextResponse.json({
      success: false,
      message: 'Internal server error'
    }, { status: 500 });
  }
}
