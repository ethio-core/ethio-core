# Database Schema

## Overview

Ethio-Core uses PostgreSQL with an event sourcing pattern. The database is organized into:
- **Event Store**: Immutable event log for all state changes
- **Projections**: Read-optimized views derived from events
- **Service Tables**: Domain-specific tables per service

## Event Store Schema

### events

The core event store table that captures all domain events.

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    version INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    
    CONSTRAINT unique_aggregate_version UNIQUE (aggregate_type, aggregate_id, version)
);

CREATE INDEX idx_events_aggregate ON events(aggregate_type, aggregate_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_created_at ON events(created_at);
```

### event_snapshots

Periodic snapshots for faster aggregate reconstruction.

```sql
CREATE TABLE event_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    version INTEGER NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_snapshot UNIQUE (aggregate_type, aggregate_id)
);
```

## Identity Service Tables

### users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    kyc_level INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_status ON users(status);
```

### identity_documents

```sql
CREATE TABLE identity_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    document_number VARCHAR(100),
    issuing_country VARCHAR(3),
    expiry_date DATE,
    verification_status VARCHAR(50) DEFAULT 'pending',
    ocr_data JSONB,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_identity_documents_user ON identity_documents(user_id);
CREATE INDEX idx_identity_documents_status ON identity_documents(verification_status);
```

### kyc_verifications

```sql
CREATE TABLE kyc_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    verification_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    risk_score DECIMAL(5,2),
    reviewer_id UUID,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_kyc_verifications_user ON kyc_verifications(user_id);
CREATE INDEX idx_kyc_verifications_status ON kyc_verifications(status);
```

## Biometric Service Tables

### biometric_enrollments

```sql
CREATE TABLE biometric_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    biometric_type VARCHAR(50) NOT NULL,
    template_hash VARCHAR(255) NOT NULL,
    template_encrypted BYTEA NOT NULL,
    quality_score DECIMAL(5,2),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_user_biometric UNIQUE (user_id, biometric_type)
);

CREATE INDEX idx_biometric_enrollments_user ON biometric_enrollments(user_id);
```

### biometric_verifications

```sql
CREATE TABLE biometric_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    enrollment_id UUID REFERENCES biometric_enrollments(id),
    verification_type VARCHAR(50) NOT NULL,
    match_score DECIMAL(5,4),
    liveness_score DECIMAL(5,4),
    is_match BOOLEAN NOT NULL,
    is_live BOOLEAN,
    ip_address INET,
    device_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_biometric_verifications_user ON biometric_verifications(user_id);
CREATE INDEX idx_biometric_verifications_created ON biometric_verifications(created_at);
```

## Card Service Tables

### cards

```sql
CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    pan_hash VARCHAR(255) NOT NULL,
    pan_encrypted BYTEA NOT NULL,
    expiry_month INTEGER NOT NULL,
    expiry_year INTEGER NOT NULL,
    card_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    currency VARCHAR(3) DEFAULT 'ETB',
    daily_limit DECIMAL(15,2) DEFAULT 50000.00,
    monthly_limit DECIMAL(15,2) DEFAULT 500000.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cards_user ON cards(user_id);
CREATE INDEX idx_cards_status ON cards(status);
CREATE INDEX idx_cards_pan_hash ON cards(pan_hash);
```

### card_tokens

```sql
CREATE TABLE card_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID REFERENCES cards(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    token_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_card_tokens_card ON card_tokens(card_id);
CREATE INDEX idx_card_tokens_token ON card_tokens(token);
```

### dynamic_cvv

```sql
CREATE TABLE dynamic_cvv (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID REFERENCES cards(id) ON DELETE CASCADE,
    cvv_hash VARCHAR(255) NOT NULL,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_dynamic_cvv_card ON dynamic_cvv(card_id);
CREATE INDEX idx_dynamic_cvv_validity ON dynamic_cvv(valid_until);
```

## Transaction Service Tables

### transactions

```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID NOT NULL,
    user_id UUID NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    merchant_id VARCHAR(100),
    merchant_name VARCHAR(255),
    merchant_category VARCHAR(50),
    reference_number VARCHAR(100) UNIQUE,
    authorization_code VARCHAR(50),
    response_code VARCHAR(10),
    is_offline BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_transactions_card ON transactions(card_id);
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_created ON transactions(created_at);
CREATE INDEX idx_transactions_reference ON transactions(reference_number);
```

### offline_queue

```sql
CREATE TABLE offline_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID NOT NULL,
    transaction_data JSONB NOT NULL,
    offline_signature VARCHAR(512) NOT NULL,
    offline_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    retry_count INTEGER DEFAULT 0,
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_offline_queue_status ON offline_queue(status);
CREATE INDEX idx_offline_queue_card ON offline_queue(card_id);
```

### settlements

```sql
CREATE TABLE settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    settlement_date DATE NOT NULL,
    merchant_id VARCHAR(100) NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    transaction_count INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    settled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_settlements_date ON settlements(settlement_date);
CREATE INDEX idx_settlements_merchant ON settlements(merchant_id);
CREATE INDEX idx_settlements_status ON settlements(status);
```

## Security Service Tables

### audit_logs

Hash-linked audit log for tamper detection.

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    user_id UUID,
    resource_type VARCHAR(100),
    resource_id UUID,
    action VARCHAR(50) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    request_data JSONB,
    response_status INTEGER,
    hash VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_hash ON audit_logs(hash);
```

### sessions

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    refresh_token_hash VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(refresh_token_hash);
CREATE INDEX idx_sessions_active ON sessions(is_active, expires_at);
```

### roles

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    granted_by UUID,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);
```

## SSO Service Tables

### oauth_clients

```sql
CREATE TABLE oauth_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(100) UNIQUE NOT NULL,
    client_secret_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    redirect_uris TEXT[] NOT NULL,
    allowed_scopes TEXT[] DEFAULT ARRAY['openid', 'profile', 'email'],
    grant_types TEXT[] DEFAULT ARRAY['authorization_code', 'refresh_token'],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### oauth_consents

```sql
CREATE TABLE oauth_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    client_id UUID REFERENCES oauth_clients(id) ON DELETE CASCADE,
    scopes TEXT[] NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT unique_user_client_consent UNIQUE (user_id, client_id)
);

CREATE INDEX idx_oauth_consents_user ON oauth_consents(user_id);
```

### authorization_codes

```sql
CREATE TABLE authorization_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(255) UNIQUE NOT NULL,
    client_id UUID REFERENCES oauth_clients(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    redirect_uri TEXT NOT NULL,
    scopes TEXT[] NOT NULL,
    code_challenge VARCHAR(255),
    code_challenge_method VARCHAR(10),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_auth_codes_code ON authorization_codes(code);
CREATE INDEX idx_auth_codes_expires ON authorization_codes(expires_at);
```

## Projections

### application_summary

```sql
CREATE MATERIALIZED VIEW application_summary AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_applications,
    COUNT(*) FILTER (WHERE status = 'approved') as approved,
    COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
    COUNT(*) FILTER (WHERE status = 'pending') as pending
FROM kyc_verifications
GROUP BY DATE(created_at)
ORDER BY date DESC;

CREATE UNIQUE INDEX idx_application_summary_date ON application_summary(date);
```

### agent_performance

```sql
CREATE MATERIALIZED VIEW agent_performance AS
SELECT 
    reviewer_id as agent_id,
    DATE(reviewed_at) as date,
    COUNT(*) as reviews_completed,
    AVG(EXTRACT(EPOCH FROM (reviewed_at - created_at))) as avg_review_time_seconds,
    COUNT(*) FILTER (WHERE status = 'approved') as approvals,
    COUNT(*) FILTER (WHERE status = 'rejected') as rejections
FROM kyc_verifications
WHERE reviewer_id IS NOT NULL
GROUP BY reviewer_id, DATE(reviewed_at);

CREATE UNIQUE INDEX idx_agent_performance ON agent_performance(agent_id, date);
```

## Database Maintenance

### Refresh Materialized Views

```sql
-- Run periodically (e.g., every hour)
REFRESH MATERIALIZED VIEW CONCURRENTLY application_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY agent_performance;
```

### Partition Events Table (Optional for large scale)

```sql
-- Partition by month for better performance
CREATE TABLE events_partitioned (
    LIKE events INCLUDING ALL
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2026_03 PARTITION OF events_partitioned
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
```
