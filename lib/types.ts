// Core data types for the Digital Identity & Transaction System

export interface User {
  id: string;
  fullName: string;
  phone: string;
  nationalId: string;
  email?: string;
  biometricEmbedding: number[]; // Simulated face/fingerprint embedding
  pin: string; // Hashed PIN
  createdAt: string;
  kycStatus: 'pending' | 'verified' | 'rejected';
  walletBalance: number;
}

export interface VirtualCard {
  id: string;
  userId: string;
  tokenizedNumber: string; // Tokenized card number (not raw)
  lastFourDigits: string;
  expiryDate: string;
  cvvSeed: string; // Seed for dynamic CVV generation
  cryptoKeyId: string; // Reference to cryptographic key
  status: 'active' | 'frozen' | 'expired';
  createdAt: string;
  dailyLimit: number;
  spentToday: number;
}

export interface Transaction {
  id: string;
  fromUserId: string;
  toUserId: string;
  fromCardId: string;
  amount: number;
  currency: string;
  status: 'pending' | 'completed' | 'failed' | 'offline_queued';
  type: 'payment' | 'transfer' | 'withdrawal' | 'deposit';
  fraudScore: number;
  createdAt: string;
  syncedAt?: string;
  description?: string;
}

export interface OfflineTransaction {
  id: string;
  transaction: Omit<Transaction, 'id' | 'status' | 'syncedAt'>;
  queuedAt: string;
  syncStatus: 'queued' | 'syncing' | 'synced' | 'failed';
  retryCount: number;
}

export interface AuthSession {
  userId: string;
  token: string;
  expiresAt: string;
  mfaVerified: boolean;
}

export interface BiometricVerification {
  userId: string;
  embedding: number[];
  similarityScore: number;
  verified: boolean;
  timestamp: string;
}

// API Request/Response types
export interface RegisterRequest {
  fullName: string;
  phone: string;
  nationalId: string;
  email?: string;
  pin: string;
  biometricData: string; // Base64 encoded biometric capture
}

export interface RegisterResponse {
  success: boolean;
  userId?: string;
  message: string;
}

export interface LoginRequest {
  phone: string;
  pin?: string;
  biometricData?: string;
}

export interface LoginResponse {
  success: boolean;
  token?: string;
  user?: Omit<User, 'pin' | 'biometricEmbedding'>;
  message: string;
}

export interface CreateCardRequest {
  userId: string;
  dailyLimit?: number;
}

export interface CreateCardResponse {
  success: boolean;
  card?: Omit<VirtualCard, 'cvvSeed' | 'cryptoKeyId'>;
  message: string;
}

export interface PaymentRequest {
  fromUserId: string;
  toUserId: string;
  cardId: string;
  amount: number;
  description?: string;
  isOffline?: boolean;
}

export interface PaymentResponse {
  success: boolean;
  transaction?: Transaction;
  message: string;
  fraudAlert?: boolean;
}

export interface VerifyBiometricRequest {
  userId: string;
  biometricData: string;
}

export interface VerifyBiometricResponse {
  success: boolean;
  verified: boolean;
  similarityScore: number;
  message: string;
}
