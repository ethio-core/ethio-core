# Ethio-Core: Ethiopia's First Event-Sourced Financial Infrastructure

[![CI](https://github.com/ethio-core/ethio-core/actions/workflows/ci.yml/badge.svg)](https://github.com/ethio-core/ethio-core/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-✓-blue.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-✓-blue.svg)](https://kubernetes.io/)
[![Event Sourcing](https://img.shields.io/badge/event--sourcing-✓-green.svg)](https://martinfowler.com/eaaDev/EventSourcing.html)

## 🚀 Overview

**Ethio-Core** is a comprehensive, production-ready financial infrastructure platform built for the **Kifiya Inspire 3.0 Hackathon**. It combines all five core challenge areas into a unified, event-sourced system:

| Challenge Area | Implementation |
|----------------|----------------|
| **A. AI-Driven Biometric Verification** | Face recognition, liveness detection, deepfake detection, voice biometrics, fairness metrics |
| **B. Intelligent eKYC Orchestration** | Fayda National ID integration, OCR+NLP, synthetic identity detection, KYC portability |
| **C. Digital Identity System** | Identity lifecycle, selective disclosure, secure vault, identity recovery |
| **D. Federated SSO** | OAuth2/OIDC, consent management, cross-border federation, biometric-backed SSO |
| **E. Card-Based Identity & Transaction** | Virtual cards, biometric binding, offline payments, dynamic CVV, tokenization |

## 🏆 Key features

- **Immutable Event Store**: Every action is recorded as an append-only event — complete audit trail
- **Cryptographic Hash Chain**: SHA-256 tamper-evident security — bank-grade integrity
- **Temporal Queries**: "Time-travel" audit capability — ask "what was the state at 2:00 PM?"
- **Gas Town Pattern**: Agent memory survives crashes — zero data loss
- **Optimistic Concurrency**: Prevents double-spending — handles race conditions
- **Fayda Integration**: Native Ethiopian National ID support — local relevance
- **Offline Payments**: Sequence-protected QR vouchers — financial inclusion
# ETHIO-CORE - COMPLETE SYSTEM ARCHITECTURE DIAGRAMS
## DIAGRAM 1: HIGH-LEVEL SYSTEM ARCHITECTURE
```mermaid
graph TB
    subgraph EXTERNAL["EXTERNAL ACTORS"]
        USER[👤 End User]
        MERCHANT[🏪 Merchant]
        ADMIN[👨‍💼 Admin/Regulator]
        AI_AGENT[🤖 AI Agents]
    end

    subgraph PRESENTATION["PRESENTATION LAYER"]
        UI[React/Next.js Frontend<br/>Digital Wallet UI]
        CAM[Camera Module<br/>WebRTC + MediaPipe]
        ADMIN_UI[Admin Dashboard<br/>Recharts + AG Grid]
    end

    subgraph GATEWAY["API GATEWAY LAYER"]
        NGINX[Nginx Reverse Proxy<br/>SSL + Load Balancing]
        AUTH[Auth Middleware<br/>JWT + Rate Limiting]
        WS[WebSocket Server<br/>Real-time Updates]
    end

    subgraph SERVICES["7 CORE MICROSERVICES"]
        direction TB
        M1[Module 1: Identity & KYC<br/>Fayda Integration + OCR]
        M2[Module 2: Biometric & AI<br/>Face + Liveness + Fraud]
        M3[Module 3: Card Management<br/>Issuance + Tokenization + CVV]
        M4[Module 4: Transaction Engine<br/>Processing + Offline + Settlement]
        M5[Module 5: Security & Audit<br/>Auth + Encryption + Integrity]
        M6[Module 6: Federated SSO<br/>OAuth2/OIDC + Consent]
        M7[Module 7: Frontend UI<br/>Digital Wallet Experience]
    end

    subgraph EVENT_STORE["EVENT STORE LAYER (The Ledger)"]
        ES1[(events<br/>Append-Only)]
        ES2[(event_streams<br/>Version Tracking)]
        ES3[(projections<br/>Read Models)]
        HASH[🔗 SHA-256 Hash Chain]
    end

    subgraph DATA["DATA STORAGE"]
        PG[(PostgreSQL<br/>Encrypted PII)]
        VDB[(Qdrant<br/>Biometric Vectors)]
        REDIS[(Redis<br/>Sessions + Cache)]
        MINIO[(MinIO<br/>Documents)]
    end

    USER --> UI
    MERCHANT --> UI
    ADMIN --> ADMIN_UI
    AI_AGENT --> AUTH

    UI --> NGINX
    ADMIN_UI --> NGINX
    CAM --> M2

    NGINX --> AUTH
    AUTH --> M1
    AUTH --> M2
    AUTH --> M3
    AUTH --> M4
    AUTH --> M5
    AUTH --> M6
    AUTH --> M7

    M1 --> ES1
    M2 --> ES1
    M3 --> ES1
    M4 --> ES1
    M5 --> ES1
    M6 --> ES1
    
    ES1 --> HASH
    ES1 --> ES3
    
    M1 --> PG
    M2 --> VDB
    M3 --> REDIS
    M4 --> REDIS
    M5 --> PG
    M6 --> PG
    M7 --> ES3
```
# DIAGRAM 2: EVENT SOURCING ARCHITECTURE
```mermaid
graph LR
    subgraph WRITE["WRITE PATH (Commands)"]
        direction TB
        CMD[Command Handler] --> AGG[Aggregate]
        AGG --> VALIDATE{Validate<br/>Business Rules}
        VALIDATE -->|Valid| APPEND[Append Events]
        VALIDATE -->|Invalid| ERROR[Domain Error]
        APPEND --> ES[(Event Store)]
    end

    subgraph STORE["EVENT STORE (Immutable)"]
        direction TB
        E1[Event 1: IdentityCreated]
        E2[Event 2: KYCVerified]
        E3[Event 3: CardIssued]
        E4[Event 4: PaymentProcessed]
        E5[Event 5: ...]
    end

    subgraph READ["READ PATH (Queries)"]
        direction TB
        DAEMON[Projection Daemon] --> POLL[Poll New Events]
        POLL --> APPLY[Apply to Projections]
        APPLY --> P1[ApplicationSummary]
        APPLY --> P2[ComplianceAuditView]
        APPLY --> P3[TransactionHistory]
    end

    subgraph QUERY["QUERY INTERFACE"]
        API[Query API] --> P1
        API --> P2
        API --> P3
    end

    CMD --> ES
    ES --> DAEMON
```
# DIAGRAM 3: CRYPTOGRAPHIC HASH CHAIN
```mermaid
graph LR
    subgraph CHAIN["EVENT STREAM HASH CHAIN"]
        direction LR
        E1["Event 1<br/>IdentityCreated<br/>Hash: H1<br/>Prev: 0"]
        E2["Event 2<br/>KYCVerified<br/>Hash: H2<br/>Prev: H1"]
        E3["Event 3<br/>CardIssued<br/>Hash: H3<br/>Prev: H2"]
        E4["Event 4<br/>PaymentProcessed<br/>Hash: H4<br/>Prev: H3"]
        E5["Event 5<br/>...<br/>Hash: H5<br/>Prev: H4"]
    end

    subgraph VERIFY["INTEGRITY VERIFICATION"]
        V1["Verify H1"]
        V2["Verify H2 = SHA256(H1 + Event2)"]
        V3["Verify H3 = SHA256(H2 + Event3)"]
        V4["Verify H4 = SHA256(H3 + Event4)"]
        RESULT{Chain Valid?}
        
        V1 --> V2
        V2 --> V3
        V3 --> V4
        V4 --> RESULT
    end

    E1 --> V1
    E2 --> V2
    E3 --> V3
    E4 --> V4
    E5 --> V4

    RESULT -->|Yes| PASS["✅ No Tampering"]
    RESULT -->|No| FAIL["❌ Tamper Detected"]
```
# DIAGRAM 4: TRANSACTION FLOW WITH OPTIMISTIC CONCURRENCY
```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant F as Frontend
    participant T as Transaction Service
    participant B as Biometric Service
    participant C as Card Service
    participant ES as Event Store

    rect rgb(200, 220, 240)
        Note over U,ES: TWO AGENTS PROCESS SAME TRANSACTION

        par Agent A
            U->>F: Payment Request
            F->>T: POST /transaction/process
            T->>ES: load_stream("transaction-{id}")
            ES-->>T: Version 3
            T->>B: Verify Biometric
            B-->>T: Verified
            T->>C: Validate Card
            C-->>T: Valid
            T->>ES: append(events, expected_version=3)
        and Agent B (Concurrent)
            U->>F: Payment Request
            F->>T: POST /transaction/process
            T->>ES: load_stream("transaction-{id}")
            ES-->>T: Version 3
            T->>B: Verify Biometric
            B-->>T: Verified
            T->>C: Validate Card
            C-->>T: Valid
            T->>ES: append(events, expected_version=3)
        end

        Note over ES: Agent A succeeds first
        ES-->>T: Agent A → Version 4 ✅
        ES-->>T: Agent B → OptimisticConcurrencyError ❌

        T->>T: Agent B reloads stream
        T->>ES: load_stream("transaction-{id}")
        ES-->>T: Version 4
        T->>T: Detect duplicate
        T-->>F: Already processed
    end
```
# DIAGRAM 5: OFFLINE PAYMENT FLOW
```mermaid
sequenceDiagram
    autonumber
    participant U as User (Offline)
    participant M as Merchant
    participant Q as Local Queue
    participant S as Ethio-Core System
    participant ES as Event Store

    rect rgb(200, 220, 240)
        Note over U,Q: OFFLINE PHASE
        U->>U: Generate QR<br/>Sequence: 5, Nonce, Signature
        U->>M: Display QR Code
        M->>M: Scan QR
        M->>Q: Store Voucher Locally
    end

    rect rgb(200, 240, 200)
        Note over Q,S: SYNC PHASE (When Online)
        M->>S: Submit Voucher
        S->>ES: load_stream("sequence-card")
        ES-->>S: Last Sequence: 4
        S->>S: Verify Sequence: 5 > 4 ✅
        S->>S: Verify Nonce ✅
        S->>S: Verify Signature ✅
        S->>ES: append("sequence-card", [Sequence:6], expected_version=5)
        
        alt Duplicate
            ES-->>S: OptimisticConcurrencyError
            S-->>M: Already Processed
        else Success
            ES-->>S: Version 6
            S->>S: Process Transaction
            S->>ES: append("transaction", [PaymentProcessed])
            S-->>M: Transaction Complete
        end
    end
```
# DIAGRAM 6: MODULE INTERACTION MAP
```mermaid
graph TB
    subgraph MODULES["7 CORE MODULES"]
        M1[Module 1<br/>Identity & KYC<br/>Fayda + OCR]
        M2[Module 2<br/>Biometric & AI<br/>Face + Liveness + Fraud]
        M3[Module 3<br/>Card Management<br/>Issuance + Tokenization]
        M4[Module 4<br/>Transaction Engine<br/>Processing + Offline]
        M5[Module 5<br/>Security & Audit<br/>Auth + Integrity]
        M6[Module 6<br/>Federated SSO<br/>OAuth2 + Consent]
        M7[Module 7<br/>Frontend UI<br/>Digital Wallet]
    end

    subgraph DATA["DATA LAYER"]
        ES[(Event Store)]
        PG[(PostgreSQL)]
        VDB[(Qdrant)]
        RD[(Redis)]
    end

    subgraph EXTERNAL_EXT["EXTERNAL INTEGRATIONS"]
        FAYDA[Fayda API<br/>Ethiopian National ID]
        KIF[Kifiya API<br/>Core Banking]
        VISA[Visa/Mastercard<br/>Payment Network]
    end

    M7 --> M1
    M7 --> M2
    M7 --> M3
    M7 --> M4
    M7 --> M5
    M7 --> M6

    M1 --> ES
    M2 --> ES
    M3 --> ES
    M4 --> ES
    M5 --> ES
    M6 --> ES

    M1 --> PG
    M2 --> VDB
    M3 --> RD
    M4 --> RD
    M5 --> PG

    M1 --> FAYDA
    M4 --> KIF
    M4 --> VISA

    M5 -.->|Verifies| ES
```
# DIAGRAM 7: DEPLOYMENT ARCHITECTURE (KUBERNETES)
```mermaid
graph TB
    subgraph K8S["KUBERNETES CLUSTER"]
        subgraph INGRESS["Ingress Layer"]
            NGINX_ING[Nginx Ingress Controller]
            CERT[Cert Manager<br/>Let's Encrypt]
        end

        subgraph SERVICES["Microservices Pods"]
            direction LR
            P1[Identity Pod<br/>Replicas: 3]
            P2[Biometric Pod<br/>GPU: 1, Replicas: 2]
            P3[Card Pod<br/>Replicas: 3]
            P4[Transaction Pod<br/>Replicas: 5]
            P5[Security Pod<br/>Replicas: 3]
            P6[SSO Pod<br/>Replicas: 2]
            P7[Frontend Pod<br/>Replicas: 3]
        end

        subgraph STATE["Stateful Services"]
            PG_STS[(PostgreSQL<br/>Primary + 2 Replicas)]
            RD_STS[(Redis Cluster<br/>3 Nodes)]
            QD_STS[(Qdrant Cluster<br/>3 Nodes)]
            MINIO_STS[(MinIO<br/>Object Storage)]
        end

        subgraph MONITOR["Monitoring"]
            PROM[Prometheus<br/>Metrics]
            GRAF[Grafana<br/>Dashboards]
            LOKI[Loki<br/>Logs]
        end
    end

    subgraph CLOUD["CLOUD PROVIDER"]
        LB[Load Balancer]
        STORAGE[Persistent Volumes]
    end

    LB --> NGINX_ING
    NGINX_ING --> SERVICES
    SERVICES --> STATE
    SERVICES --> PROM
    PROM --> GRAF
    STATE --> STORAGE
```
# DIAGRAM 8: TEMPORAL QUERY (TIME-TRAVEL AUDIT)
```mermaid
graph LR
    subgraph TIMELINE["EVENT TIMELINE"]
        direction LR
        T1[10:00<br/>IdentityCreated]
        T2[10:05<br/>KYCVerified]
        T3[10:10<br/>CardIssued]
        T4[10:15<br/>CardFrozen]
        T5[10:20<br/>Current Time]
    end

    subgraph QUERY["TEMPORAL QUERY"]
        Q1[Query: State at 10:12]
        Q2[Load events up to 10:12]
        Q3[Replay: IdentityCreated → KYCVerified → CardIssued]
        Q4[Result: Card Active, Limit 10,000 ETB]
    end

    subgraph QUERY2["CURRENT STATE"]
        R1[Current: Card Frozen at 10:15]
        R2[Limit: 0 ETB]
    end

    T1 --> T2 --> T3 --> T4 --> T5
    T3 -.-> Q1
    Q1 --> Q2 --> Q3 --> Q4
    T5 --> R1 --> R2

    subgraph OUTPUT["OUTPUT"]
        O1[📊 State at 10:12: Active ✅]
        O2[📊 Current State: Frozen ❌]
    end

    Q4 --> O1
    R2 --> O2
```
# DIAGRAM 9: SECURITY ARCHITECTURE LAYERS
```mermaid
graph TB
    subgraph L1["LAYER 1: PERIMETER SECURITY"]
        WAF[Web Application Firewall]
        RATE[Rate Limiting - 100 req/min]
        IP[IP Whitelisting - Admin Only]
    end

    subgraph L2["LAYER 2: TRANSPORT SECURITY"]
        TLS[TLS 1.3 Encryption]
        MTLS[mTLS - Service-to-Service]
        CERT[Certificate Pinning]
    end

    subgraph L3["LAYER 3: AUTHENTICATION"]
        OAUTH[OAuth2 / OpenID Connect]
        JWT[JWT with Scopes<br/>15-min expiry]
        BIO_MFA[Biometric MFA<br/>Face + PIN + OTP]
    end

    subgraph L4["LAYER 4: DATA PROTECTION"]
        ENC[AES-256-GCM<br/>PII Encryption]
        TOKEN[Tokenization<br/>Card Data]
        HSM[HSM Simulation<br/>Key Rotation]
    end

    subgraph L5["LAYER 5: EVENT STORE SECURITY"]
        APPEND[Append-Only<br/>No Updates/Deletes]
        HASH[Hash Chain<br/>SHA-256 Tamper Evidence]
        AUDIT[Immutable Audit<br/>All Actions Recorded]
        INTEGRITY[Periodic Integrity<br/>Chain Verification]
    end

    L1 --> L2 --> L3 --> L4 --> L5
```
# DIAGRAM 10: COMPLETE USER JOURNEY
```mermaid
flowchart TD
    START([Start]) --> STEP1

    subgraph STEP1[STEP 1: REGISTRATION - 2 minutes]
        A1[User enters phone number]
        A2[OTP verification]
        A3[IdentityCreated event]
        A4[Fayda ID linked]
    end

    STEP1 --> STEP2

    subgraph STEP2[STEP 2: BIOMETRIC ENROLLMENT - 1 minute]
        B1[User positions face in camera]
        B2[Liveness detection - blink + motion]
        B3[Face embedding extracted]
        B4[BiometricEnrolled event]
    end

    STEP2 --> STEP3

    subgraph STEP3[STEP 3: KYC VERIFICATION - 2 minutes]
        C1[User uploads Fayda ID]
        C2[OCR extracts data]
        C3[NLP verifies consistency]
        C4[KYCVerified event]
    end

    STEP3 --> STEP4

    subgraph STEP4[STEP 4: CARD ISSUANCE - 30 seconds]
        D1[User requests virtual card]
        D2[Biometric verification]
        D3[CardIssued event]
        D4[Dynamic CVV generated]
    end

    STEP4 --> STEP5

    subgraph STEP5[STEP 5: PAYMENT - 15 seconds]
        E1[User enters amount + merchant]
        E2[Biometric verification]
        E3[Risk scoring - fraud check]
        E4[PaymentProcessed event]
        E5[IntegrityCheckRun event]
    end

    STEP5 --> END([Complete])

    style STEP1 fill:#e1f5fe
    style STEP2 fill:#e8f5e9
    style STEP3 fill:#fff3e0
    style STEP4 fill:#fce4ec
    style STEP5 fill:#f3e5f5
```
## 📁 Repository Structure

```bash
ethio-core/
│
├── README.md                           # Main documentation
├── LICENSE                             # MIT License
├── docker-compose.yml                  # Local development setup
├── docker-compose.prod.yml             # Production setup
├── .env.example                        # Environment variables template
├── .gitignore                          # Python/Node/IDE ignores
├── Makefile                            # Common commands
│
├── docs/                               # Documentation
│   ├── ARCHITECTURE.md                 # System architecture
│   ├── API_REFERENCE.md                # Complete API docs
│   ├── DATABASE_SCHEMA.md              # PostgreSQL schema
│   ├── DEPLOYMENT.md                   # Deployment guide
│   ├── EVENT_CATALOGUE.md              # All event types
│   └── USER_GUIDE.md                   # End-user documentation
│
├── modules/                            # 7 Core Modules
│   │
│   ├── m1-identity/                    # Module 1: Identity & KYC
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   ├── event_handlers.py
│   │   │   ├── ocr_engine.py
│   │   │   ├── fayda_integration.py
│   │   │   └── kyc_orchestrator.py
│   │   └── tests/
│   │       ├── test_identity.py
│   │       ├── test_kyc.py
│   │       └── test_fayda.py
│   │
│   ├── m2-biometric/                   # Module 2: Biometric & AI
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── face_recognition.py
│   │   │   ├── liveness_detection.py
│   │   │   ├── fraud_detection.py
│   │   │   └── fairness_metrics.py
│   │   └── tests/
│   │
│   ├── m3-card/                        # Module 3: Card Management
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── card_issuance.py
│   │   │   ├── tokenization.py
│   │   │   └── dynamic_cvv.py
│   │   └── tests/
│   │
│   ├── m4-transaction/                 # Module 4: Transaction Engine
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── transaction_processor.py
│   │   │   ├── offline_queue.py
│   │   │   └── settlement.py
│   │   └── tests/
│   │
│   ├── m5-security/                    # Module 5: Security & Audit
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── auth_service.py
│   │   │   ├── audit_chain.py
│   │   │   └── integrity_checker.py
│   │   └── tests/
│   │
│   ├── m6-sso/                         # Module 6: Federated SSO
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── oauth2_provider.py
│   │   │   └── consent_manager.py
│   │   └── tests/
│   │
│   └── m7-frontend/                    # Module 7: Digital Wallet
│       ├── Dockerfile
│       ├── package.json
│       ├── next.config.js
│       ├── tailwind.config.js
│       ├── src/
│       │   ├── pages/
│       │   ├── components/
│       │   ├── hooks/
│       │   └── services/
│       └── tests/
│
├── event-store/                        # Event Store Infrastructure
│   ├── schema.sql                      # PostgreSQL schema
│   ├── migrations/                     # Alembic migrations
│   │   ├── versions/
│   │   └── alembic.ini
│   └── projections/                    # Read model projections
│       ├── application_summary.py
│       ├── compliance_audit.py
│       └── agent_performance.py
│
├── k8s/                                # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── postgres/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── redis/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── m1-identity/
│   ├── m2-biometric/
│   ├── m3-card/
│   ├── m4-transaction/
│   ├── m5-security/
│   ├── m6-sso/
│   ├── m7-frontend/
│   └── ingress.yaml
│
├── scripts/                           # Utility scripts
│   ├── setup.sh                        # Development setup
│   ├── run_tests.sh                    # Run all tests
│   ├── deploy.sh                       # Deploy to environment
│   └── integrity_check.py              # Run audit chain verification
│
└── .github/                            # GitHub Actions CI/CD
    └── workflows/
        ├── ci.yml                      # Continuous Integration
        ├── tests.yml                   # Test suite
        └── deploy.yml                  # Deployment pipeline
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Pydantic |
| **Event Store** | PostgreSQL 15 (append-only, immutable) |
| **AI/ML** | TensorFlow 2.15, OpenCV, MediaPipe, XGBoost, FaceNet |
| **Frontend** | Next.js 14, React, TypeScript, TailwindCSS, Shadcn UI |
| **Infrastructure** | Docker, Kubernetes, Redis, Nginx |
| **Security** | OAuth2/OIDC, JWT, AES-256, Cryptography |

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (for local development)
- Python 3.11+
- Node.js 18+
- PostgreSQL 15 (or use Docker)

### Local Development (with Docker)

```bash
# Clone the repository
git clone https://github.com/ethio-core/ethio-core.git
cd ethio-core

# Copy environment variables
cp .env.example .env

# Start all services
docker-compose up -d

# Run migrations
make migrate

# Run tests
make test

# Access services
# Frontend: http://localhost:3000
# API Gateway: http://localhost:8000
# Event Store: postgres://localhost:5432/ethio_core
```
# 🧪 Testing
```bash
# Run all tests

# Run unit tests only
pytest modules/*/tests/ -m "not integration"

# Run integration tests
pytest modules/*/tests/ -m integration

# Run concurrency tests (critical for double-spend prevention)
pytest tests/test_concurrency.py

# Run integrity tests (hash chain verification)
pytest tests/test_integrity.py
```
# 👥 Team	
- Tsegay Assefa	
- Weldesilassie	
- Chekole	
# 📝 License
MIT License - see LICENSE for details

# 🙏 Acknowledgments
- Kifiya Financial Technology for the hackathon opportunity
- Ethiopian National ID (Fayda) program for integration inspiration
- Dr. Natnael Argaw for judging and guidance

# 📞 Contact
- Organization: https://github.com/ethio-core
- Repository: https://github.com/ethio-core/ethio-core