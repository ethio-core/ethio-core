# Kifya 3.0 - Digital Identity and Payment MVP

A Next.js 16 demo application for digital identity onboarding, biometric-assisted authentication, virtual card issuance, and transaction flows.

## Tech Stack

- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS
- pnpm

## Features

- Multi-step registration with PIN setup and biometric capture UX
- Secure login with PIN and biometric flow
- In-memory demo backend with seeded accounts
- Virtual card creation and card security endpoints
- Payment and transaction APIs
- Offline queue and sync simulation

## Project Structure

- app: app routes and API endpoints
- components: UI and demo flow components
- lib: in-memory database, crypto, biometrics, and shared utilities
- styles: global styling assets

## API Endpoints

- POST /api/seed-demo
- POST /api/register
- POST /api/login
- POST /api/verify-biometric
- POST /api/create-card
- POST /api/pay
- GET /api/transactions
- POST /api/sync
- GET /api/users/[id]
- GET /api/cards/[id]/cvv

## Getting Started

### Prerequisites

- Node.js 20+
- pnpm

### Install

```bash
pnpm install
```

### Run Development Server

```bash
pnpm dev
```

Open http://localhost:3000 and use the demo flow at /demo.

## Build

```bash
pnpm build
pnpm start
```

## Demo Accounts

The app can seed two demo accounts through /api/seed-demo:

- +250700000001 / 1234
- +250700000002 / 5678

If registration returns 409, the phone is already registered in the in-memory store.

## CI

GitHub Actions workflow is defined at .github/workflows/ci.yml and runs install + build on push and pull requests.

## Notes

- The current backend uses in-memory storage for MVP/demo behavior.
- Biometric processing in this project is simulated and intended for demonstration only.
