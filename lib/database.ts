import type { User, VirtualCard, Transaction, OfflineTransaction, AuthSession } from './types';
import { generateBiometricEmbedding } from './biometrics';
import {
  generateCvvSeed,
  generateCryptoKeyId,
  generateExpiryDate,
  generateId,
  hashPin,
  tokenizeCardNumber,
} from './crypto';

class Database {
  private users: Map<string, User> = new Map();
  private cards: Map<string, VirtualCard> = new Map();
  private transactions: Map<string, Transaction> = new Map();
  private offlineQueue: Map<string, OfflineTransaction> = new Map();
  private sessions: Map<string, AuthSession> = new Map();
  private phoneIndex: Map<string, string> = new Map();

  createUser(user: User): User {
    this.users.set(user.id, user);
    this.phoneIndex.set(user.phone, user.id);
    return user;
  }

  getUserById(id: string): User | undefined {
    return this.users.get(id);
  }

  getUserByPhone(phone: string): User | undefined {
    const userId = this.phoneIndex.get(phone);
    return userId ? this.users.get(userId) : undefined;
  }

  updateUser(id: string, updates: Partial<User>): User | undefined {
    const user = this.users.get(id);
    if (user) {
      const updated = { ...user, ...updates };
      this.users.set(id, updated);
      return updated;
    }
    return undefined;
  }

  getAllUsers(): User[] {
    return Array.from(this.users.values());
  }

  createCard(card: VirtualCard): VirtualCard {
    this.cards.set(card.id, card);
    return card;
  }

  getCardById(id: string): VirtualCard | undefined {
    return this.cards.get(id);
  }

  getCardsByUserId(userId: string): VirtualCard[] {
    return Array.from(this.cards.values()).filter(card => card.userId === userId);
  }

  updateCard(id: string, updates: Partial<VirtualCard>): VirtualCard | undefined {
    const card = this.cards.get(id);
    if (card) {
      const updated = { ...card, ...updates };
      this.cards.set(id, updated);
      return updated;
    }
    return undefined;
  }

  createTransaction(transaction: Transaction): Transaction {
    this.transactions.set(transaction.id, transaction);
    return transaction;
  }

  getTransactionById(id: string): Transaction | undefined {
    return this.transactions.get(id);
  }

  getTransactionsByUserId(userId: string): Transaction[] {
    return Array.from(this.transactions.values()).filter(
      t => t.fromUserId === userId || t.toUserId === userId
    );
  }

  updateTransaction(id: string, updates: Partial<Transaction>): Transaction | undefined {
    const transaction = this.transactions.get(id);
    if (transaction) {
      const updated = { ...transaction, ...updates };
      this.transactions.set(id, updated);
      return updated;
    }
    return undefined;
  }

  getAllTransactions(): Transaction[] {
    return Array.from(this.transactions.values());
  }

  queueOfflineTransaction(offlineTx: OfflineTransaction): OfflineTransaction {
    this.offlineQueue.set(offlineTx.id, offlineTx);
    return offlineTx;
  }

  getOfflineQueue(): OfflineTransaction[] {
    return Array.from(this.offlineQueue.values());
  }

  getOfflineQueueByUserId(userId: string): OfflineTransaction[] {
    return Array.from(this.offlineQueue.values()).filter(
      t => t.transaction.fromUserId === userId
    );
  }

  updateOfflineTransaction(id: string, updates: Partial<OfflineTransaction>): OfflineTransaction | undefined {
    const offlineTx = this.offlineQueue.get(id);
    if (offlineTx) {
      const updated = { ...offlineTx, ...updates };
      this.offlineQueue.set(id, updated);
      return updated;
    }
    return undefined;
  }

  removeOfflineTransaction(id: string): boolean {
    return this.offlineQueue.delete(id);
  }

  createSession(session: AuthSession): AuthSession {
    this.sessions.set(session.token, session);
    return session;
  }

  getSessionByToken(token: string): AuthSession | undefined {
    const session = this.sessions.get(token);
    if (session && new Date(session.expiresAt) < new Date()) {
      this.sessions.delete(token);
      return undefined;
    }
    return session;
  }

  deleteSession(token: string): boolean {
    return this.sessions.delete(token);
  }

  reset(): void {
    this.users.clear();
    this.cards.clear();
    this.transactions.clear();
    this.offlineQueue.clear();
    this.sessions.clear();
    this.phoneIndex.clear();
  }

  getStats(): {
    users: number;
    cards: number;
    transactions: number;
    offlineQueue: number;
    sessions: number;
  } {
    return {
      users: this.users.size,
      cards: this.cards.size,
      transactions: this.transactions.size,
      offlineQueue: this.offlineQueue.size,
      sessions: this.sessions.size
    };
  }
}

export const db = new Database();

export type DemoSeedAccount = {
  phone: string;
  pin: string;
  fullName: string;
};

const DEMO_ACCOUNTS: DemoSeedAccount[] = [
  { phone: '+250700000001', pin: '1234', fullName: 'Amina Yusuf' },
  { phone: '+250700000002', pin: '5678', fullName: 'Brian Okello' },
];

export function seedDemoData(): DemoSeedAccount[] {
  const stats = db.getStats();
  if (stats.users > 0) {
    return DEMO_ACCOUNTS;
  }

  const createdAtOld = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();

  const user1: User = {
    id: generateId('usr'),
    fullName: DEMO_ACCOUNTS[0].fullName,
    phone: DEMO_ACCOUNTS[0].phone,
    nationalId: 'RWA-12345678',
    email: 'amina@example.com',
    biometricEmbedding: generateBiometricEmbedding('face_demo_amina'),
    pin: hashPin(DEMO_ACCOUNTS[0].pin),
    createdAt: createdAtOld,
    kycStatus: 'verified',
    walletBalance: 1000,
  };

  const user2: User = {
    id: generateId('usr'),
    fullName: DEMO_ACCOUNTS[1].fullName,
    phone: DEMO_ACCOUNTS[1].phone,
    nationalId: 'UGA-87654321',
    email: 'brian@example.com',
    biometricEmbedding: generateBiometricEmbedding('face_demo_brian'),
    pin: hashPin(DEMO_ACCOUNTS[1].pin),
    createdAt: createdAtOld,
    kycStatus: 'verified',
    walletBalance: 500,
  };

  db.createUser(user1);
  db.createUser(user2);

  const { tokenized: tokenized1, lastFour: lastFour1 } = tokenizeCardNumber();
  const card1: VirtualCard = {
    id: generateId('card'),
    userId: user1.id,
    tokenizedNumber: tokenized1,
    lastFourDigits: lastFour1,
    expiryDate: generateExpiryDate(),
    cvvSeed: generateCvvSeed(),
    cryptoKeyId: generateCryptoKeyId(),
    status: 'active',
    createdAt: new Date().toISOString(),
    dailyLimit: 5000,
    spentToday: 0,
  };
  db.createCard(card1);

  const { tokenized: tokenized2, lastFour: lastFour2 } = tokenizeCardNumber();
  const card2: VirtualCard = {
    id: generateId('card'),
    userId: user2.id,
    tokenizedNumber: tokenized2,
    lastFourDigits: lastFour2,
    expiryDate: generateExpiryDate(),
    cvvSeed: generateCvvSeed(),
    cryptoKeyId: generateCryptoKeyId(),
    status: 'active',
    createdAt: new Date().toISOString(),
    dailyLimit: 5000,
    spentToday: 0,
  };
  db.createCard(card2);

  const txOld1At = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString();
  const txOld2At = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000 - 60 * 60 * 1000).toISOString();

  const tx1: Transaction = {
    id: generateId('tx'),
    fromUserId: user1.id,
    toUserId: user2.id,
    fromCardId: card1.id,
    amount: 200,
    currency: 'USD',
    status: 'completed',
    type: 'payment',
    fraudScore: 12,
    createdAt: txOld1At,
    syncedAt: txOld1At,
    description: 'Demo payment (seed)',
  };
  db.createTransaction(tx1);

  const tx2: Transaction = {
    id: generateId('tx'),
    fromUserId: user2.id,
    toUserId: user1.id,
    fromCardId: card2.id,
    amount: 50,
    currency: 'USD',
    status: 'completed',
    type: 'payment',
    fraudScore: 45,
    createdAt: txOld2At,
    syncedAt: txOld2At,
    description: 'Demo payment (seed)',
  };
  db.createTransaction(tx2);

  db.updateUser(user1.id, { walletBalance: user1.walletBalance - tx1.amount + tx2.amount });
  db.updateUser(user2.id, { walletBalance: user2.walletBalance + tx1.amount - tx2.amount });
  db.updateCard(card1.id, { spentToday: tx1.amount });
  db.updateCard(card2.id, { spentToday: tx2.amount });

  const queuedAt = new Date(Date.now() - 30 * 60 * 1000).toISOString();
  const offlineTx: OfflineTransaction = {
    id: generateId('offline'),
    queuedAt,
    syncStatus: 'queued',
    retryCount: 0,
    transaction: {
      fromUserId: user1.id,
      toUserId: user2.id,
      fromCardId: card1.id,
      amount: 120,
      currency: 'USD',
      type: 'payment',
      fraudScore: 5,
      createdAt: queuedAt,
      description: 'Offline payment (seed)',
    },
  };
  db.queueOfflineTransaction(offlineTx);

  return DEMO_ACCOUNTS;
}
