// Biometric processing utilities (simulated for MVP)

import { createHash } from 'crypto';

// Simulated face/fingerprint embedding dimension
const EMBEDDING_DIMENSION = 128;

// Generate a biometric embedding from input data
// In production, this would use a real ML model (FaceNet, etc.)
export function generateBiometricEmbedding(biometricData: string): number[] {
  // Create a deterministic embedding from the input
  const hash = createHash('sha512').update(biometricData).digest('hex');
  
  const embedding: number[] = [];
  for (let i = 0; i < EMBEDDING_DIMENSION; i++) {
    // Extract values from hash and normalize to [-1, 1]
    const hexPair = hash.slice((i * 2) % hash.length, (i * 2) % hash.length + 2);
    const value = (parseInt(hexPair, 16) / 255) * 2 - 1;
    embedding.push(value);
  }
  
  // Normalize the embedding (L2 normalization)
  const magnitude = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
  return embedding.map(val => val / magnitude);
}

// Calculate cosine similarity between two embeddings
export function calculateSimilarity(embedding1: number[], embedding2: number[]): number {
  if (embedding1.length !== embedding2.length) {
    throw new Error('Embedding dimensions must match');
  }
  
  let dotProduct = 0;
  let magnitude1 = 0;
  let magnitude2 = 0;
  
  for (let i = 0; i < embedding1.length; i++) {
    dotProduct += embedding1[i] * embedding2[i];
    magnitude1 += embedding1[i] * embedding1[i];
    magnitude2 += embedding2[i] * embedding2[i];
  }
  
  magnitude1 = Math.sqrt(magnitude1);
  magnitude2 = Math.sqrt(magnitude2);
  
  if (magnitude1 === 0 || magnitude2 === 0) {
    return 0;
  }
  
  return dotProduct / (magnitude1 * magnitude2);
}

// Verify biometric match
export function verifyBiometric(
  storedEmbedding: number[],
  inputEmbedding: number[],
  threshold: number = 0.85
): { verified: boolean; similarityScore: number } {
  const similarityScore = calculateSimilarity(storedEmbedding, inputEmbedding);
  
  return {
    verified: similarityScore >= threshold,
    similarityScore: Math.round(similarityScore * 100) / 100
  };
}

// Perform liveness detection (simulated)
// In production, this would analyze multiple frames, check for eye blinks, etc.
export function performLivenessCheck(biometricData: string): {
  isLive: boolean;
  confidence: number;
  checks: {
    eyeBlink: boolean;
    headMovement: boolean;
    textureAnalysis: boolean;
  };
} {
  // Simulated liveness checks based on input data
  const hash = createHash('md5').update(biometricData).digest('hex');
  const confidence = (parseInt(hash.slice(0, 4), 16) % 20 + 80) / 100; // 80-99%
  
  return {
    isLive: confidence > 0.85,
    confidence,
    checks: {
      eyeBlink: parseInt(hash[0], 16) > 5,
      headMovement: parseInt(hash[1], 16) > 4,
      textureAnalysis: parseInt(hash[2], 16) > 3
    }
  };
}

// Add noise to embedding for anti-spoofing (returns slightly different embedding each capture)
export function addBiometricNoise(embedding: number[], noiseLevel: number = 0.02): number[] {
  return embedding.map(val => {
    const noise = (Math.random() - 0.5) * 2 * noiseLevel;
    return val + noise;
  });
}
