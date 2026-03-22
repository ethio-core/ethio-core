.PHONY: help setup install migrate test lint format clean docker-up docker-down deploy

help:
@echo "Ethio-Core Makefile Commands:"
@echo "  make setup       - Setup development environment"
@echo "  make install     - Install all dependencies"
@echo "  make migrate     - Run database migrations"
@echo "  make test        - Run all tests"
@echo "  make lint        - Run linters"
@echo "  make format      - Format code"
@echo "  make clean       - Clean cache and build files"
@echo "  make docker-up   - Start Docker services"
@echo "  make docker-down - Stop Docker services"
@echo "  make deploy      - Deploy to Kubernetes"

setup:
@echo "Setting up development environment..."
python -m venv venv
source venv/bin/activate && pip install -r requirements.txt
cd modules/m7-frontend && npm install

install:
@echo "Installing dependencies..."
pip install -r requirements.txt
cd modules/m7-frontend && npm install

migrate:
@echo "Running database migrations..."
alembic upgrade head

test:
@echo "Running tests..."
pytest tests/ -v --cov=modules --cov-report=html
cd modules/m7-frontend && npm test

lint:
@echo "Running linters..."
ruff check modules/
black --check modules/
cd modules/m7-frontend && npm run lint

format:
@echo "Formatting code..."
black modules/
isort modules/
cd modules/m7-frontend && npm run format

clean:
@echo "Cleaning cache and build files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
rm -rf .mypy_cache .ruff_cache

docker-up:
@echo "Starting Docker services..."
docker-compose up -d
@echo "Services started:"
@echo "  - PostgreSQL: localhost:5432"
@echo "  - Redis: localhost:6379"
@echo "  - Qdrant: localhost:6333"
@echo "  - MinIO: localhost:9000"
@echo "  - Frontend: http://localhost:3000"
@echo "  - API Gateway: http://localhost:8000"

docker-down:
@echo "Stopping Docker services..."
docker-compose down

docker-logs:
@echo "Showing Docker logs..."
docker-compose logs -f

deploy:
@echo "Deploying to Kubernetes..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/redis/
kubectl apply -f k8s/m1-identity/
kubectl apply -f k8s/m2-biometric/
kubectl apply -f k8s/m3-card/
kubectl apply -f k8s/m4-transaction/
kubectl apply -f k8s/m5-security/
kubectl apply -f k8s/m6-sso/
kubectl apply -f k8s/m7-frontend/
kubectl apply -f k8s/ingress.yaml
@echo "Deployment complete. Check status: kubectl get pods -n ethio-core"
