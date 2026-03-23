// Cryptographic utilities for tokenization, hashing, and security

import { createHash, randomBytes } from 'crypto';

// Generate a unique ID
export function generateId(prefix: string = ''): string {
  const timestamp = Date.now().toString(36);
  const random = randomBytes(8).toString('hex');
  return prefix ? `${prefix}_${timestamp}${random}` : `${timestamp}${random}`;
}

// Hash a PIN using SHA-256
export function hashPin(pin: string): string {
  return createHash('sha256').update(pin).digest('hex');
}

// Verify PIN against hash
export function verifyPin(pin: string, hash: string): boolean {
  return hashPin(pin) === hash;
}

// Tokenize a card number (never store raw card numbers)
export function tokenizeCardNumber(): { tokenized: string; lastFour: string } {
  // Generate a random 16-digit card number (for simulation)
  const cardNumber = Array.from({ length: 16 }, () => 
    Math.floor(Math.random() * 10)
  ).join('');
  
  const lastFour = cardNumber.slice(-4);
  
  // Create a secure token from the card number
  const token = createHash('sha256')
    .update(cardNumber + randomBytes(16).toString('hex'))
    .digest('hex');
  
  return { tokenized: token, lastFour };
}

// Generate a seed for dynamic CVV
export function generateCvvSeed(): string {
  return randomBytes(32).toString('hex');
}

// Generate dynamic CVV based on seed and time
export function generateDynamicCvv(seed: string, timestamp?: number): string {
  const time = timestamp || Math.floor(Date.now() / 30000); // Changes every 30 seconds
  const hash = createHash('sha256')
    .update(seed + time.toString())
    .digest('hex');
  
  // Extract 3 digits from the hash
  const cvv = parseInt(hash.slice(0, 6), 16) % 1000;
  return cvv.toString().padStart(3, '0');
}

// Generate a cryptographic key ID (simulated HSM key reference)
export function generateCryptoKeyId(): string {
  return `hsm_key_${randomBytes(16).toString('hex')}`;
}

// Generate expiry date (3 years from now)
export function generateExpiryDate(): string {
  const now = new Date();
  now.setFullYear(now.getFullYear() + 3);
  const month = (now.getMonth() + 1).toString().padStart(2, '0');
  const year = now.getFullYear().toString().slice(-2);
  return `${month}/${year}`;
}

// Generate auth token
export function generateAuthToken(): string {
  return randomBytes(32).toString('hex');
}

// Simple encryption for sensitive data (simulation)
export function encryptData(data: string, key: string): string {
  // In production, use proper AES encryption
  const combined = data + key;
  return Buffer.from(combined).toString('base64');
}
