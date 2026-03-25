# Architecture Overview

## System Architecture

Ethio-Core follows a microservices architecture with event-driven communication patterns, designed for scalability, resilience, and maintainability.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Load Balancer / CDN                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Gateway / Ingress                              │
│                    (Authentication, Rate Limiting, Routing)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
         ┌─────────────┬───────────────┼───────────────┬─────────────┐
         ▼             ▼               ▼               ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Identity   │ │  Biometric  │ │    Card     │ │ Transaction │ │  Security   │
│   Service   │ │   Service   │ │   Service   │ │   Service   │ │   Service   │
│  (m1)       │ │  (m2)       │ │  (m3)       │ │  (m4)       │ │  (m5)       │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │               │               │
       └───────────────┴───────────────┼───────────────┴───────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Event Store (PostgreSQL)                          │
│                    (Event Sourcing, CQRS, Audit Trail)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Redis Cluster                                   │
│                    (Caching, Sessions, Rate Limiting)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Design Principles

### 1. Microservices Architecture
- **Loose Coupling**: Each service is independently deployable
- **High Cohesion**: Services own their domain logic completely
- **API-First**: All inter-service communication via REST APIs
- **Database per Service**: Each service manages its own data

### 2. Event-Driven Architecture
- **Event Sourcing**: All state changes stored as immutable events
- **CQRS**: Separate read and write models for optimization
- **Eventually Consistent**: Services sync through event propagation
- **Audit Trail**: Complete history of all operations

### 3. Security by Design
- **Zero Trust**: All requests authenticated and authorized
- **Defense in Depth**: Multiple security layers
- **Encryption**: Data encrypted at rest and in transit
- **Audit Logging**: Hash-linked audit chains

## Service Descriptions

### M1 - Identity Service
**Purpose**: Manages user identity, KYC verification, and document processing.

**Responsibilities**:
- OCR document processing
- Fayda (National ID) integration
- KYC orchestration and verification
- Identity data management

**Key APIs**:
- `POST /api/v1/identity/verify` - Start KYC verification
- `POST /api/v1/identity/ocr` - Process document OCR
- `GET /api/v1/identity/{user_id}` - Get identity status

### M2 - Biometric Service
**Purpose**: Handles biometric authentication and fraud detection.

**Responsibilities**:
- Face recognition and matching
- Liveness detection
- Fraud detection algorithms
- Fairness metrics monitoring

**Key APIs**:
- `POST /api/v1/biometric/verify` - Verify biometric data
- `POST /api/v1/biometric/enroll` - Enroll new biometric
- `POST /api/v1/biometric/liveness` - Check liveness

### M3 - Card Service
**Purpose**: Manages virtual and physical card operations.

**Responsibilities**:
- Card issuance and lifecycle
- PAN tokenization
- Dynamic CVV generation
- Card controls and limits

**Key APIs**:
- `POST /api/v1/cards/issue` - Issue new card
- `POST /api/v1/cards/tokenize` - Tokenize card
- `GET /api/v1/cards/{card_id}/cvv` - Get dynamic CVV

### M4 - Transaction Service
**Purpose**: Processes financial transactions with offline support.

**Responsibilities**:
- Real-time transaction processing
- Offline transaction queuing
- Settlement and reconciliation
- Transaction limits enforcement

**Key APIs**:
- `POST /api/v1/transactions` - Process transaction
- `POST /api/v1/transactions/offline` - Queue offline transaction
- `GET /api/v1/transactions/{tx_id}` - Get transaction status

### M5 - Security Service
**Purpose**: Provides authentication, authorization, and audit.

**Responsibilities**:
- JWT token management
- Role-based access control (RBAC)
- Hash-linked audit logging
- Integrity verification

**Key APIs**:
- `POST /api/v1/auth/login` - Authenticate user
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/audit/logs` - Get audit logs

### M6 - SSO Service
**Purpose**: Provides OAuth2/OpenID Connect provider functionality.

**Responsibilities**:
- OAuth2 authorization server
- Consent management
- Token issuance
- Client management

**Key APIs**:
- `GET /oauth2/authorize` - Authorization endpoint
- `POST /oauth2/token` - Token endpoint
- `POST /oauth2/revoke` - Revoke token

### M7 - Frontend
**Purpose**: User-facing web application.

**Responsibilities**:
- User registration and onboarding
- Dashboard and account management
- Card management interface
- Transaction history

## Data Flow

### User Registration Flow
```
┌────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│Frontend│────▶│ Security │────▶│ Identity │────▶│Biometric │
└────────┘     └──────────┘     └──────────┘     └──────────┘
     │              │                │                │
     │              ▼                ▼                ▼
     │         ┌─────────────────────────────────────────┐
     └────────▶│            Event Store                  │
               └─────────────────────────────────────────┘
```

### Transaction Flow
```
┌────────┐     ┌────────────┐     ┌──────────┐     ┌──────────┐
│Frontend│────▶│Transaction │────▶│   Card   │────▶│ Security │
└────────┘     └────────────┘     └──────────┘     └──────────┘
                    │                                    │
                    ▼                                    ▼
               ┌─────────────────────────────────────────────┐
               │            Event Store                       │
               └─────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11, Pydantic |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Container | Docker, Kubernetes |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus, Grafana (planned) |

## Security Architecture

### Authentication Flow
1. User submits credentials
2. Security service validates and issues JWT
3. JWT contains user ID, roles, and expiration
4. Services validate JWT on each request

### Authorization (RBAC)
```python
roles = {
    "admin": ["*"],
    "user": ["read:own", "write:own"],
    "agent": ["read:users", "write:kyc"],
    "auditor": ["read:audit", "read:logs"]
}
```

### Audit Chain
```
Event N: { data, hash: SHA256(data + hash(N-1)) }
Event N-1: { data, hash: SHA256(data + hash(N-2)) }
...
Event 0: { data, hash: SHA256(data) }
```

## Scalability Considerations

### Horizontal Scaling
- Services are stateless and can be replicated
- Load balancing distributes traffic
- Database connection pooling

### Vertical Scaling
- Resource limits configurable per service
- Memory and CPU allocation in Kubernetes

### Caching Strategy
- Redis for session data
- Redis for rate limiting counters
- Application-level caching for static data

## Deployment Architecture

### Development
- Docker Compose for local development
- Hot reloading enabled
- Mock external services

### Production
- Kubernetes cluster deployment
- Multiple replicas per service
- Rolling updates for zero downtime
- Health checks and auto-healing
