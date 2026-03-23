import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/database';
import { generateId, hashPin } from '@/lib/crypto';
import { generateBiometricEmbedding, performLivenessCheck } from '@/lib/biometrics';
import type { User, RegisterRequest, RegisterResponse } from '@/lib/types';

export async function POST(request: NextRequest): Promise<NextResponse<RegisterResponse>> {
  try {
    const body: RegisterRequest = await request.json();
    const { fullName, phone, nationalId, email, pin, biometricData } = body;

    if (!fullName || !phone || !nationalId || !pin || !biometricData) {
      return NextResponse.json({
        success: false,
        message: 'Missing required fields: fullName, phone, nationalId, pin, biometricData'
      }, { status: 400 });
    }

    if (!/^\d{4,6}$/.test(pin)) {
      return NextResponse.json({
        success: false,
        message: 'PIN must be 4-6 digits'
      }, { status: 400 });
    }

    const existingUser = db.getUserByPhone(phone);
    if (existingUser) {
      return NextResponse.json({
        success: false,
        message: 'User with this phone number already exists'
      }, { status: 409 });
    }

    const livenessResult = performLivenessCheck(biometricData);
    if (!livenessResult.isLive) {
      return NextResponse.json({
        success: false,
        message: 'Biometric liveness check failed. Please try again with a live capture.'
      }, { status: 400 });
    }

    const biometricEmbedding = generateBiometricEmbedding(biometricData);

    const user: User = {
      id: generateId('usr'),
      fullName,
      phone,
      nationalId,
      email,
      biometricEmbedding,
      pin: hashPin(pin),
      createdAt: new Date().toISOString(),
      kycStatus: 'verified',
      walletBalance: 1000
    };

    db.createUser(user);

    return NextResponse.json({
      success: true,
      userId: user.id,
      message: 'User registered successfully. KYC status: verified'
    }, { status: 201 });

  } catch (error) {
    console.error('Registration error:', error);
    return NextResponse.json({
      success: false,
      message: 'Internal server error during registration'
    }, { status: 500 });
  }
}

export async function GET(): Promise<NextResponse> {
  return NextResponse.json({
    requirements: {
      fullName: 'string (required) - Full legal name',
      phone: 'string (required) - Phone number with country code',
      nationalId: 'string (required) - National ID number',
      email: 'string (optional) - Email address',
      pin: 'string (required) - 4-6 digit PIN',
      biometricData: 'string (required) - Base64 encoded biometric capture'
    },
    example: {
      fullName: 'John Doe',
      phone: '+254712345678',
      nationalId: '12345678',
      email: 'john@example.com',
      pin: '1234',
      biometricData: 'base64_encoded_face_capture_data'
    }
  });
}
