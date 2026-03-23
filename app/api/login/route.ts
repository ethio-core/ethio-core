// POST /api/login - User Authentication (Biometric + PIN)

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';
import { verifyPin, generateAuthToken } from '@/lib/crypto';
import { generateBiometricEmbedding, verifyBiometric, performLivenessCheck } from '@/lib/biometrics';
import type { LoginRequest, LoginResponse, AuthSession } from '@/lib/types';

export async function POST(request: NextRequest): Promise<NextResponse<LoginResponse>> {
  try {
    const body: LoginRequest = await request.json();
    const { phone, pin, biometricData } = body;

    // Validate required fields
    if (!phone) {
      return NextResponse.json({
        success: false,
        message: 'Missing required field: phone'
      }, { status: 400 });
    }

    // At least one auth method required
    if (!pin && !biometricData) {
      return NextResponse.json({
        success: false,
        message: 'At least one authentication method required: pin or biometricData'
      }, { status: 400 });
    }

    // Find user
    const user = db.getUserByPhone(phone);
    if (!user) {
      return NextResponse.json({
        success: false,
        message: 'User not found'
      }, { status: 404 });
    }

    let pinVerified = false;
    let biometricVerified = false;
    let biometricScore = 0;

    // Verify PIN if provided
    if (pin) {
      pinVerified = verifyPin(pin, user.pin);
      if (!pinVerified) {
        return NextResponse.json({
          success: false,
          message: 'Invalid PIN'
        }, { status: 401 });
      }
    }

    // Verify biometric if provided
    if (biometricData) {
      // Perform liveness check first
      const livenessResult = performLivenessCheck(biometricData);
      if (!livenessResult.isLive) {
        return NextResponse.json({
          success: false,
          message: 'Biometric liveness check failed'
        }, { status: 401 });
      }

      // Generate embedding from input and compare
      const inputEmbedding = generateBiometricEmbedding(biometricData);
      const verificationResult = verifyBiometric(user.biometricEmbedding, inputEmbedding);
      
      biometricVerified = verificationResult.verified;
      biometricScore = verificationResult.similarityScore;

      if (!biometricVerified) {
        return NextResponse.json({
          success: false,
          message: `Biometric verification failed. Similarity: ${biometricScore}`
        }, { status: 401 });
      }
    }

    // Determine MFA status (both methods verified)
    const mfaVerified = pinVerified && biometricVerified;

    // Create session
    const token = generateAuthToken();
    const expiresAt = new Date();
    expiresAt.setHours(expiresAt.getHours() + 24); // 24 hour session

    const session: AuthSession = {
      userId: user.id,
      token,
      expiresAt: expiresAt.toISOString(),
      mfaVerified
    };

    db.createSession(session);

    // Get user's cards
    const cards = db.getCardsByUserId(user.id);

    return NextResponse.json({
      success: true,
      token,
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
      message: mfaVerified 
        ? 'Login successful with MFA' 
        : `Login successful with ${pinVerified ? 'PIN' : 'biometric'} authentication`,
      authDetails: {
        mfaVerified,
        pinVerified,
        biometricVerified,
        biometricScore,
        sessionExpiresAt: session.expiresAt,
        cardsCount: cards.length
      }
    }, { status: 200 });

  } catch (error) {
    console.error('Login error:', error);
    return NextResponse.json({
      success: false,
      message: 'Internal server error during login'
    }, { status: 500 });
  }
}

// GET /api/login - Get login requirements
export async function GET(): Promise<NextResponse> {
  return NextResponse.json({
    requirements: {
      phone: 'string (required) - Phone number used during registration',
      pin: 'string (optional) - 4-6 digit PIN',
      biometricData: 'string (optional) - Base64 encoded biometric capture'
    },
    authMethods: [
      'PIN only - Basic authentication',
      'Biometric only - Face/fingerprint authentication',
      'PIN + Biometric - Multi-factor authentication (recommended)'
    ],
    example: {
      phone: '+254712345678',
      pin: '1234',
      biometricData: 'base64_encoded_face_capture_data'
    }
  });
}
