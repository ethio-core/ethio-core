// POST /api/create-card - Create Virtual Card

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';
import { 
  generateId, 
  tokenizeCardNumber, 
  generateCvvSeed, 
  generateCryptoKeyId,
  generateExpiryDate 
} from '@/lib/crypto';
import type { VirtualCard, CreateCardRequest, CreateCardResponse } from '@/lib/types';

export async function POST(request: NextRequest): Promise<NextResponse<CreateCardResponse>> {
  try {
    const body: CreateCardRequest = await request.json();
    const { userId, dailyLimit = 5000 } = body;

    // Validate required fields
    if (!userId) {
      return NextResponse.json({
        success: false,
        message: 'Missing required field: userId'
      }, { status: 400 });
    }

    // Verify user exists
    const user = db.getUserById(userId);
    if (!user) {
      return NextResponse.json({
        success: false,
        message: 'User not found'
      }, { status: 404 });
    }

    // Check KYC status
    if (user.kycStatus !== 'verified') {
      return NextResponse.json({
        success: false,
        message: `Cannot create card: KYC status is ${user.kycStatus}`
      }, { status: 403 });
    }

    // Check if user already has an active card
    const existingCards = db.getCardsByUserId(userId);
    const activeCard = existingCards.find(c => c.status === 'active');
    if (activeCard) {
      return NextResponse.json({
        success: false,
        message: 'User already has an active card',
        card: {
          id: activeCard.id,
          userId: activeCard.userId,
          tokenizedNumber: activeCard.tokenizedNumber,
          lastFourDigits: activeCard.lastFourDigits,
          expiryDate: activeCard.expiryDate,
          status: activeCard.status,
          createdAt: activeCard.createdAt,
          dailyLimit: activeCard.dailyLimit,
          spentToday: activeCard.spentToday
        }
      }, { status: 409 });
    }

    // Generate tokenized card number
    const { tokenized, lastFour } = tokenizeCardNumber();

    // Create virtual card
    const card: VirtualCard = {
      id: generateId('card'),
      userId,
      tokenizedNumber: tokenized,
      lastFourDigits: lastFour,
      expiryDate: generateExpiryDate(),
      cvvSeed: generateCvvSeed(),
      cryptoKeyId: generateCryptoKeyId(),
      status: 'active',
      createdAt: new Date().toISOString(),
      dailyLimit,
      spentToday: 0
    };

    db.createCard(card);

    // Return card without sensitive data
    return NextResponse.json({
      success: true,
      card: {
        id: card.id,
        userId: card.userId,
        tokenizedNumber: card.tokenizedNumber,
        lastFourDigits: card.lastFourDigits,
        expiryDate: card.expiryDate,
        status: card.status,
        createdAt: card.createdAt,
        dailyLimit: card.dailyLimit,
        spentToday: card.spentToday
      },
      message: 'Virtual card created successfully'
    }, { status: 201 });

  } catch (error) {
    console.error('Card creation error:', error);
    return NextResponse.json({
      success: false,
      message: 'Internal server error during card creation'
    }, { status: 500 });
  }
}

// GET /api/create-card - Get card creation requirements
export async function GET(): Promise<NextResponse> {
  return NextResponse.json({
    requirements: {
      userId: 'string (required) - User ID from registration',
      dailyLimit: 'number (optional) - Daily spending limit, default: 5000'
    },
    example: {
      userId: 'usr_abc123',
      dailyLimit: 5000
    },
    cardFeatures: [
      'Tokenized card number (PCI compliant)',
      'Dynamic CVV (changes every 30 seconds)',
      'HSM-protected cryptographic keys',
      'Configurable daily spending limits'
    ]
  });
}
