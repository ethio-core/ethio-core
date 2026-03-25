/**
 * API Service for Ethio-Core Platform
 * Browser: same-origin `/api/v1` (Next.js rewrites → MVP API). Server: full URL.
 */

function getApiBase(): string {
  if (typeof window !== 'undefined') {
    return ''
  }
  return process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'
}

interface ApiResponse<T> {
  data?: T
  error?: string
  status: number
}

class ApiService {
  private token: string | null = null

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token')
    }
  }

  private baseUrl(): string {
    return getApiBase()
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token')
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    }
    if (!isForm) {
      headers['Content-Type'] = 'application/json'
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    try {
      const response = await fetch(`${this.baseUrl()}${endpoint}`, {
        ...options,
        headers,
      })

      const text = await response.text()
      let data: unknown = undefined
      if (text) {
        try {
          data = JSON.parse(text) as unknown
        } catch {
          data = text
        }
      }

      if (!response.ok) {
        const errBody = data as { detail?: string }
        return {
          error: typeof errBody?.detail === 'string' ? errBody.detail : 'An error occurred',
          status: response.status,
        }
      }

      return { data: data as T, status: response.status }
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
        status: 0,
      }
    }
  }

  // Authentication
  async login(email: string, password: string) {
    return this.request<{ access_token: string; refresh_token: string }>(
      '/api/v1/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    )
  }

  async logout() {
    const result = await this.request('/api/v1/auth/logout', { method: 'POST' })
    this.clearToken()
    return result
  }

  async refreshToken(refreshToken: string) {
    return this.request<{ access_token: string }>('/api/v1/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
  }

  async getMe() {
    return this.request<{ id: string; email: string; name: string; role: string }>('/api/v1/auth/me')
  }

  // Identity Service
  async getCustomers(params?: { page?: number; limit?: number; status?: string }) {
    const query = new URLSearchParams(params as Record<string, string>).toString()
    return this.request<{ items: Customer[]; total: number }>(
      `/api/v1/identity/customers?${query}`
    )
  }

  async getCustomer(id: string) {
    return this.request<Customer>(`/api/v1/identity/customers/${id}`)
  }

  async createCustomer(data: CreateCustomerRequest) {
    return this.request<Customer>('/api/v1/identity/customers', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async initiateKyc(customerId: string) {
    return this.request<KycSession>(`/api/v1/identity/customers/${customerId}/kyc`, {
      method: 'POST',
    })
  }

  async uploadDocument(customerId: string, documentType: string, file: File) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', documentType)

    return this.request<Document>(`/api/v1/identity/customers/${customerId}/documents`, {
      method: 'POST',
      headers: {},
      body: formData,
    })
  }

  // Biometric Service
  async enrollFace(customerId: string, imageData: string) {
    return this.request<BiometricEnrollment>('/api/v1/biometric/face/enroll', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId, image_data: imageData }),
    })
  }

  async verifyFace(customerId: string, imageData: string) {
    return this.request<BiometricVerification>('/api/v1/biometric/face/verify', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId, image_data: imageData }),
    })
  }

  async checkLiveness(imageData: string) {
    return this.request<LivenessResult>('/api/v1/biometric/liveness', {
      method: 'POST',
      body: JSON.stringify({ image_data: imageData }),
    })
  }

  // Card Service
  async getCards(customerId?: string) {
    const query = customerId ? `?customer_id=${customerId}` : ''
    return this.request<{ items: Card[]; total: number }>(`/api/v1/card/cards${query}`)
  }

  async getCard(cardId: string) {
    return this.request<Card>(`/api/v1/card/cards/${cardId}`)
  }

  async requestCard(data: CardRequest) {
    return this.request<Card>('/api/v1/card/cards', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async activateCard(cardId: string) {
    return this.request<Card>(`/api/v1/card/cards/${cardId}/activate`, {
      method: 'POST',
    })
  }

  async blockCard(cardId: string, reason: string) {
    return this.request<Card>(`/api/v1/card/cards/${cardId}/block`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    })
  }

  async setPin(cardId: string, pin: string) {
    return this.request(`/api/v1/card/cards/${cardId}/pin`, {
      method: 'POST',
      body: JSON.stringify({ pin }),
    })
  }

  async getDynamicCvv(cardId: string) {
    return this.request<{ cvv: string; expires_at: string }>(
      `/api/v1/card/cards/${cardId}/dynamic-cvv`
    )
  }

  // Transaction Service
  async getTransactions(params?: {
    page?: number
    limit?: number
    customer_id?: string
    card_id?: string
    status?: string
    from_date?: string
    to_date?: string
  }) {
    const query = new URLSearchParams(params as Record<string, string>).toString()
    return this.request<{ items: Transaction[]; total: number }>(
      `/api/v1/transaction/transactions?${query}`
    )
  }

  async getTransaction(id: string) {
    return this.request<Transaction>(`/api/v1/transaction/transactions/${id}`)
  }

  async initiateTransfer(data: TransferRequest) {
    return this.request<Transaction>('/api/v1/transaction/transfer', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async reverseTransaction(transactionId: string, reason: string) {
    return this.request<Transaction>(
      `/api/v1/transaction/transactions/${transactionId}/reverse`,
      {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }
    )
  }

  // Security Service
  async getAuditLogs(params?: { page?: number; limit?: number; user_id?: string }) {
    const query = new URLSearchParams(params as Record<string, string>).toString()
    return this.request<{ items: AuditLog[]; total: number }>(
      `/api/v1/security/audit-logs?${query}`
    )
  }

  async getSecurityAlerts(params?: { page?: number; limit?: number; severity?: string }) {
    const query = new URLSearchParams(params as Record<string, string>).toString()
    return this.request<{ items: SecurityAlert[]; total: number }>(
      `/api/v1/security/alerts?${query}`
    )
  }

  async verifyIntegrity() {
    return this.request<IntegrityReport>('/api/v1/security/integrity/verify')
  }

  async resolveSecurityAlert(alertId: string) {
    return this.request<{ ok: boolean }>(`/api/v1/security/alerts/${alertId}/resolve`, {
      method: 'POST',
    })
  }

  async getKycSessions() {
    return this.request<{ items: KycApplicationRow[] }>('/api/v1/identity/kyc/sessions')
  }

  // Dashboard Stats
  async getDashboardStats() {
    return this.request<DashboardStats>('/api/v1/stats/dashboard')
  }
}

export interface KycApplicationRow {
  id: string
  customer_name: string
  email: string
  status: string
  steps_completed: string[]
  risk_score: number | null
  submitted_at: string
  verified_at: string | null
}

// Types
export interface Customer {
  id: string
  fayda_id?: string
  first_name: string
  last_name: string
  email: string
  phone_number: string
  date_of_birth: string
  kyc_status: 'pending' | 'in_progress' | 'verified' | 'rejected'
  risk_level: 'low' | 'medium' | 'high'
  created_at: string
  updated_at: string
}

export interface CreateCustomerRequest {
  first_name: string
  last_name: string
  email: string
  phone_number: string
  date_of_birth: string
}

export interface KycSession {
  id: string
  customer_id: string
  status: string
  steps_completed: string[]
  created_at: string
}

export interface Document {
  id: string
  customer_id: string
  document_type: string
  status: string
  uploaded_at: string
}

export interface BiometricEnrollment {
  id: string
  customer_id: string
  status: string
  enrolled_at: string
}

export interface BiometricVerification {
  verified: boolean
  confidence: number
  message: string
}

export interface LivenessResult {
  is_live: boolean
  confidence: number
  checks_passed: string[]
}

export interface Card {
  id: string
  customer_id: string
  customer_name?: string
  card_number_masked: string
  card_type: 'virtual' | 'physical'
  status: 'pending' | 'active' | 'blocked' | 'expired'
  expiry_date: string
  created_at: string
}

export interface CardRequest {
  customer_id: string
  card_type: 'virtual' | 'physical'
}

export interface Transaction {
  id: string
  customer_id: string
  customer_name?: string
  card_id?: string
  type: 'credit' | 'debit' | 'transfer'
  amount: number
  currency: string
  status: 'pending' | 'authorized' | 'completed' | 'failed' | 'reversed'
  description: string
  created_at: string
}

export interface TransferRequest {
  from_customer_id: string
  to_customer_id: string
  amount: number
  currency: string
  description?: string
}

export interface AuditLog {
  id: string
  user_id: string
  user_email?: string
  action: string
  resource_type: string
  resource_id: string
  details: Record<string, unknown>
  ip_address: string
  timestamp: string
  hash: string
}

export interface SecurityAlert {
  id: string
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  message: string
  user_id?: string
  resolved: boolean
  created_at: string
}

export interface IntegrityReport {
  status: 'valid' | 'invalid'
  records_checked: number
  invalid_records: string[]
  checked_at: string
}

export interface DashboardActivity {
  id: string
  type: string
  description: string
  status: string
  timestamp: string
}

export interface DashboardStats {
  total_customers: number
  active_cards: number
  transactions_today: number
  transaction_volume_today: number
  pending_kyc: number
  security_alerts: number
  growth_rates: {
    customers: number
    transactions: number
  }
  chart_transactions_week?: { name: string; transactions: number }[]
  chart_volume_months?: { name: string; volume: number }[]
  recent_activity?: DashboardActivity[]
}

export const api = new ApiService()
export default api
