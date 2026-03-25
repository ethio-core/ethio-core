# API Reference

## Overview

All Ethio-Core APIs follow REST conventions and return JSON responses. Authentication is required for most endpoints using JWT Bearer tokens.

## Base URLs

| Service | Development | Production |
|---------|-------------|------------|
| Identity | `http://localhost:8001` | `https://api.ethio-core.com/identity` |
| Biometric | `http://localhost:8002` | `https://api.ethio-core.com/biometric` |
| Card | `http://localhost:8003` | `https://api.ethio-core.com/card` |
| Transaction | `http://localhost:8004` | `https://api.ethio-core.com/transaction` |
| Security | `http://localhost:8005` | `https://api.ethio-core.com/security` |
| SSO | `http://localhost:8006` | `https://sso.ethio-core.com` |

## Authentication

### Obtaining a Token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the token in the Authorization header:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## Identity Service (M1)

### Start KYC Verification

```http
POST /api/v1/identity/verify
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_id": "uuid",
  "document_type": "national_id",
  "document_data": {
    "front_image": "base64_encoded_image",
    "back_image": "base64_encoded_image"
  }
}
```

**Response:**
```json
{
  "verification_id": "uuid",
  "status": "pending",
  "created_at": "2026-03-24T10:00:00Z"
}
```

### Process OCR

```http
POST /api/v1/identity/ocr
Authorization: Bearer {token}
Content-Type: multipart/form-data

document: (binary file)
document_type: national_id
```

**Response:**
```json
{
  "ocr_id": "uuid",
  "extracted_data": {
    "full_name": "John Doe",
    "id_number": "1234567890",
    "date_of_birth": "1990-01-15",
    "expiry_date": "2030-01-15"
  },
  "confidence_score": 0.95
}
```

### Verify with Fayda

```http
POST /api/v1/identity/fayda/verify
Authorization: Bearer {token}
Content-Type: application/json

{
  "fayda_id": "string",
  "consent_token": "string"
}
```

**Response:**
```json
{
  "verified": true,
  "match_score": 0.98,
  "details": {
    "name_match": true,
    "dob_match": true,
    "photo_match": true
  }
}
```

### Get Identity Status

```http
GET /api/v1/identity/{user_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "user_id": "uuid",
  "kyc_status": "verified",
  "verification_level": 3,
  "verified_at": "2026-03-24T10:00:00Z",
  "documents": [
    {
      "type": "national_id",
      "status": "verified",
      "verified_at": "2026-03-24T10:00:00Z"
    }
  ]
}
```

---

## Biometric Service (M2)

### Enroll Biometric

```http
POST /api/v1/biometric/enroll
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_id": "uuid",
  "biometric_type": "face",
  "data": "base64_encoded_image"
}
```

**Response:**
```json
{
  "enrollment_id": "uuid",
  "status": "enrolled",
  "created_at": "2026-03-24T10:00:00Z"
}
```

### Verify Biometric

```http
POST /api/v1/biometric/verify
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_id": "uuid",
  "biometric_type": "face",
  "data": "base64_encoded_image"
}
```

**Response:**
```json
{
  "verified": true,
  "confidence_score": 0.97,
  "liveness_passed": true
}
```

### Check Liveness

```http
POST /api/v1/biometric/liveness
Authorization: Bearer {token}
Content-Type: application/json

{
  "video_frames": ["base64_frame1", "base64_frame2", "base64_frame3"],
  "challenge_response": {
    "blink_detected": true,
    "head_movement": true
  }
}
```

**Response:**
```json
{
  "is_live": true,
  "confidence": 0.95,
  "checks_passed": ["blink", "head_movement", "texture_analysis"]
}
```

---

## Card Service (M3)

### Issue Card

```http
POST /api/v1/cards/issue
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_id": "uuid",
  "card_type": "virtual",
  "currency": "ETB",
  "daily_limit": 50000.00
}
```

**Response:**
```json
{
  "card_id": "uuid",
  "masked_pan": "****-****-****-1234",
  "expiry_month": 3,
  "expiry_year": 2029,
  "card_type": "virtual",
  "status": "active",
  "created_at": "2026-03-24T10:00:00Z"
}
```

### Tokenize Card

```http
POST /api/v1/cards/tokenize
Authorization: Bearer {token}
Content-Type: application/json

{
  "card_id": "uuid",
  "token_type": "payment"
}
```

**Response:**
```json
{
  "token": "tok_live_xxxxxxxxxxxx",
  "token_type": "payment",
  "expires_at": "2026-03-24T11:00:00Z"
}
```

### Get Dynamic CVV

```http
GET /api/v1/cards/{card_id}/cvv
Authorization: Bearer {token}
```

**Response:**
```json
{
  "cvv": "123",
  "valid_until": "2026-03-24T10:05:00Z",
  "seconds_remaining": 300
}
```

### Get Card Details

```http
GET /api/v1/cards/{card_id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "card_id": "uuid",
  "masked_pan": "****-****-****-1234",
  "card_type": "virtual",
  "status": "active",
  "balance": 10000.00,
  "currency": "ETB",
  "daily_limit": 50000.00,
  "daily_spent": 5000.00
}
```

---

## Transaction Service (M4)

### Process Transaction

```http
POST /api/v1/transactions
Authorization: Bearer {token}
Content-Type: application/json

{
  "card_id": "uuid",
  "amount": 1000.00,
  "currency": "ETB",
  "merchant": {
    "id": "merchant_123",
    "name": "Example Store",
    "category": "retail"
  },
  "type": "purchase"
}
```

**Response:**
```json
{
  "transaction_id": "uuid",
  "status": "completed",
  "amount": 1000.00,
  "currency": "ETB",
  "balance_after": 9000.00,
  "timestamp": "2026-03-24T10:00:00Z"
}
```

### Queue Offline Transaction

```http
POST /api/v1/transactions/offline
Authorization: Bearer {token}
Content-Type: application/json

{
  "card_id": "uuid",
  "amount": 500.00,
  "currency": "ETB",
  "merchant_id": "merchant_123",
  "offline_timestamp": "2026-03-24T09:55:00Z",
  "offline_signature": "signed_payload"
}
```

**Response:**
```json
{
  "queue_id": "uuid",
  "status": "queued",
  "position": 3,
  "estimated_processing": "2026-03-24T10:01:00Z"
}
```

### Get Transaction History

```http
GET /api/v1/transactions?user_id={user_id}&limit=20&offset=0
Authorization: Bearer {token}
```

**Response:**
```json
{
  "transactions": [
    {
      "transaction_id": "uuid",
      "type": "purchase",
      "amount": 1000.00,
      "currency": "ETB",
      "status": "completed",
      "merchant_name": "Example Store",
      "timestamp": "2026-03-24T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

---

## Security Service (M5)

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

### Register

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "phone": "+251911234567",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "status": "pending_verification",
  "created_at": "2026-03-24T10:00:00Z"
}
```

### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Get Audit Logs

```http
GET /api/v1/audit/logs?start_date=2026-03-01&end_date=2026-03-24
Authorization: Bearer {token}
```

**Response:**
```json
{
  "logs": [
    {
      "id": "uuid",
      "event_type": "USER_LOGIN",
      "user_id": "uuid",
      "ip_address": "192.168.1.1",
      "timestamp": "2026-03-24T10:00:00Z",
      "hash": "sha256_hash",
      "previous_hash": "previous_sha256_hash"
    }
  ],
  "integrity_verified": true
}
```

---

## SSO Service (M6)

### OAuth2 Authorization

```http
GET /oauth2/authorize?
  response_type=code&
  client_id=ethio_client&
  redirect_uri=https://app.example.com/callback&
  scope=openid profile email&
  state=random_state_string
```

### Exchange Token

```http
POST /oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=authorization_code&
redirect_uri=https://app.example.com/callback&
client_id=ethio_client&
client_secret=client_secret
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "id_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Revoke Token

```http
POST /oauth2/revoke
Content-Type: application/x-www-form-urlencoded

token=access_token&
token_type_hint=access_token&
client_id=ethio_client&
client_secret=client_secret
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "field": "Additional context"
    }
  },
  "request_id": "uuid"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request data |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limiting

API requests are rate limited per user/client:

| Endpoint Type | Limit |
|---------------|-------|
| Authentication | 10 requests/minute |
| Read operations | 100 requests/minute |
| Write operations | 30 requests/minute |
| Transaction processing | 60 requests/minute |

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1679669400
```
