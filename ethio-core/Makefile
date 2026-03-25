# Ethio-Core Makefile
# ====================

.PHONY: help setup dev test lint build deploy clean

# Default target
help:
	@echo "Ethio-Core - Available Commands"
	@echo "================================"
	@echo "  make setup      - Initial project setup"
	@echo "  make dev        - Start development environment"
	@echo "  make test       - Run all tests"
	@echo "  make lint       - Run linters"
	@echo "  make build      - Build all Docker images"
	@echo "  make push       - Push images to registry"
	@echo "  make deploy     - Deploy to Kubernetes"
	@echo "  make clean      - Clean up containers and volumes"
	@echo "  make logs       - View service logs"
	@echo "  make shell      - Open shell in a service"

# =============================================================================
# Setup
# =============================================================================
setup:
	@echo "Setting up Ethio-Core..."
	@cp -n .env.example .env || true
	@chmod +x scripts/*.sh
	@./scripts/setup.sh
	@echo "Setup complete!"

# =============================================================================
# Development
# =============================================================================
dev:
	@echo "Starting development environment..."
	docker-compose up -d
	@echo "Services starting..."
	@echo "Frontend: http://localhost:3000"
	@echo "Identity API: http://localhost:8001"
	@echo "Biometric API: http://localhost:8002"
	@echo "Card API: http://localhost:8003"
	@echo "Transaction API: http://localhost:8004"
	@echo "Security API: http://localhost:8005"
	@echo "SSO API: http://localhost:8006"

dev-build:
	docker-compose up -d --build

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-service:
	@read -p "Service name: " service; \
	docker-compose logs -f $$service

shell:
	@read -p "Service name: " service; \
	docker-compose exec $$service /bin/sh

# =============================================================================
# Testing
# =============================================================================
test:
	@echo "Running all tests..."
	@./scripts/run_tests.sh

test-identity:
	cd modules/m1-identity && python -m pytest tests/ -v

test-biometric:
	cd modules/m2-biometric && python -m pytest tests/ -v

test-card:
	cd modules/m3-card && python -m pytest tests/ -v

test-transaction:
	cd modules/m4-transaction && python -m pytest tests/ -v

test-security:
	cd modules/m5-security && python -m pytest tests/ -v

test-sso:
	cd modules/m6-sso && python -m pytest tests/ -v

test-frontend:
	cd modules/m7-frontend && npm test

test-coverage:
	@echo "Running tests with coverage..."
	@for module in m1-identity m2-biometric m3-card m4-transaction m5-security m6-sso; do \
		echo "Testing $$module..."; \
		cd modules/$$module && python -m pytest tests/ --cov=. --cov-report=html || true; \
		cd ../..; \
	done

# =============================================================================
# Linting
# =============================================================================
lint:
	@echo "Running linters..."
	@for module in m1-identity m2-biometric m3-card m4-transaction m5-security m6-sso; do \
		echo "Linting $$module..."; \
		cd modules/$$module && ruff check . || true; \
		cd ../..; \
	done
	cd modules/m7-frontend && npm run lint || true

lint-fix:
	@for module in m1-identity m2-biometric m3-card m4-transaction m5-security m6-sso; do \
		cd modules/$$module && ruff check . --fix || true; \
		cd ../..; \
	done
	cd modules/m7-frontend && npm run lint:fix || true

# =============================================================================
# Build
# =============================================================================
build:
	@echo "Building all Docker images..."
	docker-compose build

build-prod:
	@echo "Building production images..."
	docker build -t ethio-identity:latest modules/m1-identity
	docker build -t ethio-biometric:latest modules/m2-biometric
	docker build -t ethio-card:latest modules/m3-card
	docker build -t ethio-transaction:latest modules/m4-transaction
	docker build -t ethio-security:latest modules/m5-security
	docker build -t ethio-sso:latest modules/m6-sso
	docker build -t ethio-frontend:latest modules/m7-frontend

push:
	@echo "Pushing images to registry..."
	@if [ -z "$(REGISTRY)" ]; then echo "REGISTRY not set"; exit 1; fi
	docker tag ethio-identity:latest $(REGISTRY)/ethio-identity:$(VERSION)
	docker tag ethio-biometric:latest $(REGISTRY)/ethio-biometric:$(VERSION)
	docker tag ethio-card:latest $(REGISTRY)/ethio-card:$(VERSION)
	docker tag ethio-transaction:latest $(REGISTRY)/ethio-transaction:$(VERSION)
	docker tag ethio-security:latest $(REGISTRY)/ethio-security:$(VERSION)
	docker tag ethio-sso:latest $(REGISTRY)/ethio-sso:$(VERSION)
	docker tag ethio-frontend:latest $(REGISTRY)/ethio-frontend:$(VERSION)
	docker push $(REGISTRY)/ethio-identity:$(VERSION)
	docker push $(REGISTRY)/ethio-biometric:$(VERSION)
	docker push $(REGISTRY)/ethio-card:$(VERSION)
	docker push $(REGISTRY)/ethio-transaction:$(VERSION)
	docker push $(REGISTRY)/ethio-security:$(VERSION)
	docker push $(REGISTRY)/ethio-sso:$(VERSION)
	docker push $(REGISTRY)/ethio-frontend:$(VERSION)

# =============================================================================
# Deployment
# =============================================================================
deploy:
	@echo "Deploying to Kubernetes..."
	@./scripts/deploy.sh

deploy-dry-run:
	kubectl apply -f k8s/ --dry-run=client

k8s-status:
	kubectl get pods -n ethio-core
	kubectl get services -n ethio-core

k8s-logs:
	@read -p "Pod name: " pod; \
	kubectl logs -f $$pod -n ethio-core

# =============================================================================
# Database
# =============================================================================
db-migrate:
	cd event-store && alembic upgrade head

db-rollback:
	cd event-store && alembic downgrade -1

db-shell:
	docker-compose exec postgres psql -U ethio -d ethio_core

db-backup:
	docker-compose exec postgres pg_dump -U ethio ethio_core > backup_$(shell date +%Y%m%d_%H%M%S).sql

# =============================================================================
# Security
# =============================================================================
security-check:
	@echo "Running security checks..."
	@./scripts/integrity_check.py

audit:
	@echo "Running security audit..."
	@for module in m1-identity m2-biometric m3-card m4-transaction m5-security m6-sso; do \
		cd modules/$$module && pip-audit || true; \
		cd ../..; \
	done
	cd modules/m7-frontend && npm audit || true

# =============================================================================
# Cleanup
# =============================================================================
clean:
	@echo "Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f

clean-all:
	@echo "Deep cleaning..."
	docker-compose down -v --remove-orphans
	docker system prune -af --volumes
	rm -rf modules/m7-frontend/node_modules
	rm -rf modules/m7-frontend/.next
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
