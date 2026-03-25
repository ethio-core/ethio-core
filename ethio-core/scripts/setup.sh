#!/bin/bash

# Ethio-Core Setup Script
# This script sets up the development environment

set -e

echo "=========================================="
echo "  Ethio-Core Development Setup"
echo "=========================================="

# Check prerequisites
echo ""
echo "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

echo "✓ Docker installed"
echo "✓ Docker Compose installed"

# Create .env file if not exists
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠️  Please update the .env file with your configuration"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/postgres
mkdir -p data/redis
mkdir -p logs
echo "✓ Directories created"

# Generate JWT keys if not exists
if [ ! -f keys/jwt_private.pem ]; then
    echo ""
    echo "Generating JWT keys..."
    mkdir -p keys
    openssl genrsa -out keys/jwt_private.pem 2048
    openssl rsa -in keys/jwt_private.pem -pubout -out keys/jwt_public.pem
    echo "✓ JWT keys generated"
fi

# Build Docker images
echo ""
echo "Building Docker images..."
docker-compose build

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "To start the development environment, run:"
echo "  docker-compose up -d"
echo ""
echo "Services will be available at:"
echo "  - Frontend:       http://localhost:3000"
echo "  - Identity API:   http://localhost:8001"
echo "  - Biometric API:  http://localhost:8002"
echo "  - Card API:       http://localhost:8003"
echo "  - Transaction API: http://localhost:8004"
echo "  - Security API:   http://localhost:8005"
echo "  - SSO API:        http://localhost:8006"
echo "  - Event Store:    http://localhost:8010"
echo ""
echo "Default credentials:"
echo "  Email: admin@ethio-core.com"
echo "  Password: admin123"
echo ""
