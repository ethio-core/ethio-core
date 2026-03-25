# Event Catalogue

## Overview

Ethio-Core uses event sourcing to capture all state changes as immutable events. This document catalogs all domain events in the system.

## Event Structure

All events follow a standard structure:

```json
{
  "id": "uuid",
  "event_type": "EVENT_NAME",
  "aggregate_type": "AggregateType",
  "aggregate_id": "uuid",
  "version": 1,
  "payload": { ... },
  "metadata": {
    "user_id": "uuid",
    "correlation_id": "uuid",
    "causation_id": "uuid",
    "timestamp": "2026-03-24T10:00:00Z",
    "source_service": "service-name"
  },
  "created_at": "2026-03-24T10:00:00Z"
}
```

---

## Identity Service Events

### USER_CREATED

Emitted when a new user account is created.

```json
{
  "event_type": "USER_CREATED",
  "aggregate_type": "User",
  "payload": {
    "user_id": "uuid",
    "email": "user@example.com",
    "phone": "+251911234567",
    "full_name": "John Doe",
    "created_at": "2026-03-24T10:00:00Z"
  }
}
```

**Consumers**: Security Service, Notification Service

### USER_UPDATED

Emitted when user profile information is updated.

```json
{
  "event_type": "USER_UPDATED",
  "aggregate_type": "User",
  "payload": {
    "user_id": "uuid",
    "changes": {
      "full_name": {
        "old": "John Doe",
        "new": "John M. Doe"
      }
    },
    "updated_at": "2026-03-24T10:00:00Z"
  }
}
```

### KYC_INITIATED

Emitted when KYC verification process starts.

```json
{
  "event_type": "KYC_INITIATED",
  "aggregate_type": "KYCVerification",
  "payload": {
    "verification_id": "uuid",
    "user_id": "uuid",
    "verification_type": "full_kyc",
    "documents_submitted": ["national_id", "selfie"],
    "initiated_at": "2026-03-24T10:00:00Z"
  }
}
```

### KYC_VERIFIED

Emitted when KYC verification is successfully completed.

```json
{
  "event_type": "KYC_VERIFIED",
  "aggregate_type": "KYCVerification",
  "payload": {
    "verification_id": "uuid",
    "user_id": "uuid",
    "kyc_level": 3,
    "verified_documents": ["national_id", "selfie"],
    "risk_score": 0.15,
    "verified_by": "uuid",
    "verified_at": "2026-03-24T10:00:00Z"
  }
}
```

**Consumers**: Card Service (enables card issuance), Transaction Service (updates limits)

### KYC_REJECTED

Emitted when KYC verification is rejected.

```json
{
  "event_type": "KYC_REJECTED",
  "aggregate_type": "KYCVerification",
  "payload": {
    "verification_id": "uuid",
    "user_id": "uuid",
    "rejection_reason": "document_expired",
    "rejection_details": "National ID expired on 2025-01-15",
    "rejected_by": "uuid",
    "rejected_at": "2026-03-24T10:00:00Z"
  }
}
```

### DOCUMENT_OCR_COMPLETED

Emitted when document OCR processing completes.

```json
{
  "event_type": "DOCUMENT_OCR_COMPLETED",
  "aggregate_type": "Document",
  "payload": {
    "document_id": "uuid",
    "user_id": "uuid",
    "document_type": "national_id",
    "extracted_data": {
      "full_name": "John Doe",
      "id_number": "1234567890",
      "date_of_birth": "1990-01-15",
      "expiry_date": "2030-01-15"
    },
    "confidence_score": 0.95,
    "processed_at": "2026-03-24T10:00:00Z"
  }
}
```

### FAYDA_VERIFICATION_COMPLETED

Emitted when Fayda (National ID) verification completes.

```json
{
  "event_type": "FAYDA_VERIFICATION_COMPLETED",
  "aggregate_type": "FaydaVerification",
  "payload": {
    "verification_id": "uuid",
    "user_id": "uuid",
    "fayda_id": "string",
    "is_verified": true,
    "match_details": {
      "name_match": true,
      "dob_match": true,
      "photo_match_score": 0.98
    },
    "verified_at": "2026-03-24T10:00:00Z"
  }
}
```

---

## Biometric Service Events

### BIOMETRIC_ENROLLED

Emitted when a user enrolls their biometric data.

```json
{
  "event_type": "BIOMETRIC_ENROLLED",
  "aggregate_type": "BiometricEnrollment",
  "payload": {
    "enrollment_id": "uuid",
    "user_id": "uuid",
    "biometric_type": "face",
    "quality_score": 0.92,
    "enrolled_at": "2026-03-24T10:00:00Z"
  }
}
```

### BIOMETRIC_VERIFIED

Emitted when biometric verification succeeds.

```json
{
  "event_type": "BIOMETRIC_VERIFIED",
  "aggregate_type": "BiometricVerification",
  "payload": {
    "verification_id": "uuid",
    "user_id": "uuid",
    "biometric_type": "face",
    "match_score": 0.97,
    "liveness_score": 0.95,
    "is_live": true,
    "verified_at": "2026-03-24T10:00:00Z"
  }
}
```

### BIOMETRIC_FAILED

Emitted when biometric verification fails.

```json
{
  "event_type": "BIOMETRIC_FAILED",
  "aggregate_type": "BiometricVerification",
  "payload": {
    "verification_id": "uuid",
    "user_id": "uuid",
    "biometric_type": "face",
    "failure_reason": "liveness_check_failed",
    "match_score": 0.45,
    "liveness_score": 0.30,
    "failed_at": "2026-03-24T10:00:00Z"
  }
}
```

**Consumers**: Security Service (fraud monitoring)

### FRAUD_DETECTED

Emitted when fraud is detected during biometric verification.

```json
{
  "event_type": "FRAUD_DETECTED",
  "aggregate_type": "FraudDetection",
  "payload": {
    "detection_id": "uuid",
    "user_id": "uuid",
    "fraud_type": "presentation_attack",
    "confidence": 0.95,
    "details": {
      "attack_type": "printed_photo",
      "detection_method": "texture_analysis"
    },
    "detected_at": "2026-03-24T10:00:00Z"
  }
}
```

**Consumers**: Security Service (account freeze), Notification Service

---

## Card Service Events

### CARD_ISSUED

Emitted when a new card is issued.

```json
{
  "event_type": "CARD_ISSUED",
  "aggregate_type": "Card",
  "payload": {
    "card_id": "uuid",
    "user_id": "uuid",
    "card_type": "virtual",
    "masked_pan": "****-****-****-1234",
    "expiry_month": 3,
    "expiry_year": 2029,
    "currency": "ETB",
    "daily_limit": 50000.00,
    "issued_at": "2026-03-24T10:00:00Z"
  }
}
```

**Consumers**: Transaction Service, Notification Service

### CARD_ACTIVATED

Emitted when a card is activated.

```json
{
  "event_type": "CARD_ACTIVATED",
  "aggregate_type": "Card",
  "payload": {
    "card_id": "uuid",
    "user_id": "uuid",
    "activated_at": "2026-03-24T10:00:00Z"
  }
}
```

### CARD_BLOCKED

Emitted when a card is blocked (by user or system).

```json
{
  "event_type": "CARD_BLOCKED",
  "aggregate_type": "Card",
  "payload": {
    "card_id": "uuid",
    "user_id": "uuid",
    "block_reason": "user_requested",
    "blocked_by": "uuid",
    "blocked_at": "2026-03-24T10:00:00Z"
  }
}
```

**Consumers**: Transaction Service (reject transactions)

### CARD_TOKENIZED

Emitted when a card is tokenized.

```json
{
  "event_type": "CARD_TOKENIZED",
  "aggregate_type": "CardToken",
  "payload": {
    "token_id": "uuid",
    "card_id": "uuid",
    "token_type": "payment",
    "token_last_four": "xxxx",
    "expires_at": "2026-03-24T11:00:00Z",
    "tokenized_at": "2026-03-24T10:00:00Z"
  }
}
```

### DYNAMIC_CVV_GENERATED

Emitted when a dynamic CVV is generated.

```json
{
  "event_type": "DYNAMIC_CVV_GENERATED",
  "aggregate_type": "DynamicCVV",
  "payload": {
    "cvv_id": "uuid",
    "card_id": "uuid",
    "valid_from": "2026-03-24T10:00:00Z",
    "valid_until": "2026-03-24T10:05:00Z",
    "generated_at": "2026-03-24T10:00:00Z"
  }
}
```

---

## Transaction Service Events

### TRANSACTION_INITIATED

Emitted when a transaction is initiated.

```json
{
  "event_type": "TRANSACTION_INITIATED",
  "aggregate_type": "Transaction",
  "payload": {
    "transaction_id": "uuid",
    "card_id": "uuid",
    "user_id": "uuid",
    "transaction_type": "purchase",
    "amount": 1000.00,
    "currency": "ETB",
    "merchant": {
      "id": "merchant_123",
      "name": "Example Store",
      "category": "retail"
    },
    "initiated_at": "2026-03-24T10:00:00Z"
  }
}
```

### TRANSACTION_COMPLETED

Emitted when a transaction is successfully completed.

```json
{
  "event_type": "TRANSACTION_COMPLETED",
  "aggregate_type": "Transaction",
  "payload": {
    "transaction_id": "uuid",
    "card_id": "uuid",
    "user_id": "uuid",
    "amount": 1000.00,
    "currency": "ETB",
    "balance_before": 10000.00,
    "balance_after": 9000.00,
    "authorization_code": "AUTH123456",
    "completed_at": "2026-03-24T10:00:00Z"
  }
}
```

**Consumers**: Notification Service, Settlement Service

### TRANSACTION_DECLINED

Emitted when a transaction is declined.

```json
{
  "event_type": "TRANSACTION_DECLINED",
  "aggregate_type": "Transaction",
  "payload": {
    "transaction_id": "uuid",
    "card_id": "uuid",
    "user_id": "uuid",
    "amount": 1000.00,
    "decline_reason": "insufficient_funds",
    "decline_code": "51",
    "declined_at": "2026-03-24T10:00:00Z"
  }
}
```

### OFFLINE_TRANSACTION_QUEUED

Emitted when an offline transaction is queued.

```json
{
  "event_type": "OFFLINE_TRANSACTION_QUEUED",
  "aggregate_type": "OfflineTransaction",
  "payload": {
    "queue_id": "uuid",
    "card_id": "uuid",
    "amount": 500.00,
    "offline_timestamp": "2026-03-24T09:55:00Z",
    "queued_at": "2026-03-24T10:00:00Z"
  }
}
```

### SETTLEMENT_COMPLETED

Emitted when daily settlement completes.

```json
{
  "event_type": "SETTLEMENT_COMPLETED",
  "aggregate_type": "Settlement",
  "payload": {
    "settlement_id": "uuid",
    "settlement_date": "2026-03-24",
    "merchant_id": "merchant_123",
    "total_amount": 150000.00,
    "transaction_count": 150,
    "currency": "ETB",
    "settled_at": "2026-03-24T23:59:00Z"
  }
}
```

---

## Security Service Events

### USER_LOGIN

Emitted when a user logs in.

```json
{
  "event_type": "USER_LOGIN",
  "aggregate_type": "Session",
  "payload": {
    "session_id": "uuid",
    "user_id": "uuid",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "login_method": "password",
    "logged_in_at": "2026-03-24T10:00:00Z"
  }
}
```

### USER_LOGOUT

Emitted when a user logs out.

```json
{
  "event_type": "USER_LOGOUT",
  "aggregate_type": "Session",
  "payload": {
    "session_id": "uuid",
    "user_id": "uuid",
    "logged_out_at": "2026-03-24T10:00:00Z"
  }
}
```

### PASSWORD_CHANGED

Emitted when a user changes their password.

```json
{
  "event_type": "PASSWORD_CHANGED",
  "aggregate_type": "User",
  "payload": {
    "user_id": "uuid",
    "changed_via": "user_settings",
    "changed_at": "2026-03-24T10:00:00Z"
  }
}
```

### ROLE_ASSIGNED

Emitted when a role is assigned to a user.

```json
{
  "event_type": "ROLE_ASSIGNED",
  "aggregate_type": "UserRole",
  "payload": {
    "user_id": "uuid",
    "role": "admin",
    "granted_by": "uuid",
    "assigned_at": "2026-03-24T10:00:00Z"
  }
}
```

### AUDIT_INTEGRITY_VERIFIED

Emitted when audit chain integrity is verified.

```json
{
  "event_type": "AUDIT_INTEGRITY_VERIFIED",
  "aggregate_type": "AuditChain",
  "payload": {
    "verification_id": "uuid",
    "from_log_id": "uuid",
    "to_log_id": "uuid",
    "records_verified": 1000,
    "integrity_status": "valid",
    "verified_at": "2026-03-24T10:00:00Z"
  }
}
```

---

## SSO Service Events

### OAUTH_AUTHORIZATION_GRANTED

Emitted when OAuth authorization is granted.

```json
{
  "event_type": "OAUTH_AUTHORIZATION_GRANTED",
  "aggregate_type": "Authorization",
  "payload": {
    "authorization_id": "uuid",
    "user_id": "uuid",
    "client_id": "ethio_client",
    "scopes": ["openid", "profile", "email"],
    "granted_at": "2026-03-24T10:00:00Z"
  }
}
```

### OAUTH_TOKEN_ISSUED

Emitted when OAuth tokens are issued.

```json
{
  "event_type": "OAUTH_TOKEN_ISSUED",
  "aggregate_type": "Token",
  "payload": {
    "token_id": "uuid",
    "user_id": "uuid",
    "client_id": "ethio_client",
    "token_type": "access_token",
    "scopes": ["openid", "profile", "email"],
    "expires_at": "2026-03-24T11:00:00Z",
    "issued_at": "2026-03-24T10:00:00Z"
  }
}
```

### CONSENT_REVOKED

Emitted when a user revokes consent for an OAuth client.

```json
{
  "event_type": "CONSENT_REVOKED",
  "aggregate_type": "Consent",
  "payload": {
    "consent_id": "uuid",
    "user_id": "uuid",
    "client_id": "ethio_client",
    "revoked_at": "2026-03-24T10:00:00Z"
  }
}
```

---

## Event Routing Matrix

| Event | Producer | Consumers |
|-------|----------|-----------|
| USER_CREATED | Identity | Security, Notification |
| KYC_VERIFIED | Identity | Card, Transaction |
| BIOMETRIC_ENROLLED | Biometric | Security |
| FRAUD_DETECTED | Biometric | Security, Notification |
| CARD_ISSUED | Card | Transaction, Notification |
| CARD_BLOCKED | Card | Transaction |
| TRANSACTION_COMPLETED | Transaction | Notification, Settlement |
| USER_LOGIN | Security | Audit |
| OAUTH_TOKEN_ISSUED | SSO | Security |

## Event Versioning

Events are versioned to support schema evolution:

```json
{
  "event_type": "USER_CREATED",
  "version": "2",
  "payload": { ... }
}
```

When consuming events, services should handle multiple versions gracefully.
