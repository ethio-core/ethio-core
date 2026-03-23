// POST /api/verify-biometric - Verify Biometric Data

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';
import { generateBiometricEmbedding, verifyBiometric, performLivenessCheck } from '@/lib/biometrics';
import type { VerifyBiometricRequest, VerifyBiometricResponse } from '@/lib/types';

export async function POST(request: NextRequest): Promise<NextResponse<VerifyBiometricResponse>> {
  try {
    const body: VerifyBiometricRequest = await request.json();
    const { userId, biometricData } = body;

    // Validate required fields
    if (!userId || !biometricData) {
      return NextResponse.json({
        success: false,
        verified: false,
        similarityScore: 0,
        message: 'Missing required fields: userId, biometricData'
      }, { status: 400 });
    }

    // Find user
    const user = db.getUserById(userId);
    if (!user) {
      return NextResponse.json({
        success: false,
        verified: false,
        similarityScore: 0,
        message: 'User not found'
      }, { status: 404 });
    }

    // Perform liveness check
    const livenessResult = performLivenessCheck(biometricData);
    if (!livenessResult.isLive) {
      return NextResponse.json({
        success: false,
        verified: false,
        similarityScore: 0,
        message: 'Liveness check failed. Please ensure you are using a live capture.',
        livenessDetails: {
          confidence: livenessResult.confidence,
          checks: livenessResult.checks
        }
      }, { status: 400 });
    }

    // Generate embedding from input
    const inputEmbedding = generateBiometricEmbedding(biometricData);

    // Verify against stored embedding
    const result = verifyBiometric(user.biometricEmbedding, inputEmbedding);

    return NextResponse.json({
      success: true,
      verified: result.verified,
      similarityScore: result.similarityScore,
      message: result.verified 
        ? 'Biometric verification successful' 
        : `Biometric verification failed. Score: ${result.similarityScore} (threshold: 0.85)`,
      details: {
        livenessConfidence: livenessResult.confidence,
        livenessChecks: livenessResult.checks,
        verificationThreshold: 0.85
      }
    }, { status: 200 });

  } catch (error) {
    console.error('Biometric verification error:', error);
    return NextResponse.json({
      success: false,
      verified: false,
      similarityScore: 0,
      message: 'Internal server error during biometric verification'
    }, { status: 500 });
  }
}

// GET /api/verify-biometric - Get verification requirements
export async function GET(): Promise<NextResponse> {
  return NextResponse.json({
    requirements: {
      userId: 'string (required) - User ID to verify against',
      biometricData: 'string (required) - Base64 encoded biometric capture'
    },
    example: {
      userId: 'usr_abc123',
      biometricData: 'base64_encoded_face_capture_data'
    },
    securityFeatures: [
      'Liveness detection (anti-spoofing)',
      'Eye blink detection',
      'Head movement analysis',
      'Texture analysis',
      'Similarity threshold: 0.85'
    ]
  });
}
