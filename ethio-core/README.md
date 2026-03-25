# Ethio-Core

A production-ready monorepo for fintech, digital identity, and digital wallet systems built with microservices architecture.

## Overview

Ethio-Core is an enterprise-grade platform that provides:
- **Digital Identity Management** - KYC verification, OCR processing, Fayda integration
- **Biometric Authentication** - Face recognition, liveness detection, fraud prevention
- **Digital Wallet & Cards** - Card issuance, tokenization, dynamic CVV
- **Transaction Processing** - Real-time and offline transaction handling
- **Security & Compliance** - JWT auth, audit logging, integrity verification
- **Single Sign-On** - OAuth2 provider with consent management

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway / Ingress                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │Identity │ │Biometric│ │  Card   │ │  Trans  │ │Security │   │
│  │ Service │ │ Service │ │ Service │ │ Service │ │ Service │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │
│       │           │           │           │           │         │
│  ┌────┴───────────┴───────────┴───────────┴───────────┴────┐   │
│  │                    Event Store (PostgreSQL)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Redis (Cache/Queue)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/ethio-core.git
cd ethio-core
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start all services:
```bash
docker-compose up -d
```

4. Access the services:
- Frontend: http://localhost:3000
- Identity API: http://localhost:8001
- Biometric API: http://localhost:8002
- Card API: http://localhost:8003
- Transaction API: http://localhost:8004
- Security API: http://localhost:8005
- SSO API: http://localhost:8006

### Using Make Commands

```bash
make setup      # Initial setup
make dev        # Start development environment
make test       # Run all tests
make lint       # Run linters
make build      # Build all containers
make deploy     # Deploy to Kubernetes
```

## Project Structure

```
ethio-core/
├── docs/                    # Documentation
├── modules/                 # Microservices
│   ├── m1-identity/        # Identity & KYC service
│   ├── m2-biometric/       # Biometric authentication
│   ├── m3-card/            # Card management
│   ├── m4-transaction/     # Transaction processing
│   ├── m5-security/        # Auth & audit
│   ├── m6-sso/             # OAuth2/SSO
│   └── m7-frontend/        # Next.js frontend
├── event-store/            # Event sourcing setup
├── k8s/                    # Kubernetes configs
├── scripts/                # Utility scripts
└── .github/workflows/      # CI/CD pipelines
```

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Event Catalogue](docs/EVENT_CATALOGUE.md)
- [User Guide](docs/USER_GUIDE.md)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue or contact the development team.
