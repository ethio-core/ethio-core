# Deployment Guide

## Overview

This guide covers deploying Ethio-Core to various environments, from local development to production Kubernetes clusters.

## Prerequisites

- Docker 24.0+
- Docker Compose 2.0+
- kubectl 1.28+
- Helm 3.0+ (optional)
- Access to a container registry
- Kubernetes cluster (for production)

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/ethio-core.git
cd ethio-core

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Accessing Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Identity API | http://localhost:8001/docs |
| Biometric API | http://localhost:8002/docs |
| Card API | http://localhost:8003/docs |
| Transaction API | http://localhost:8004/docs |
| Security API | http://localhost:8005/docs |
| SSO API | http://localhost:8006/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### Development Commands

```bash
# Rebuild and restart a service
docker-compose up -d --build identity-service

# Run tests
make test

# Run linters
make lint

# View service logs
docker-compose logs -f identity-service
```

## Staging Deployment

### Build Images

```bash
# Set version tag
export VERSION=v1.0.0-rc1
export REGISTRY=your-registry.azurecr.io

# Build all images
make build-prod

# Push to registry
make push
```

### Deploy to Staging Cluster

```bash
# Configure kubectl for staging
kubectl config use-context staging-cluster

# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply secrets
kubectl apply -f k8s/secrets.yaml

# Apply configmaps
kubectl apply -f k8s/configmap.yaml

# Deploy PostgreSQL and Redis
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/redis-service.yaml

# Wait for databases
kubectl wait --for=condition=ready pod -l app=postgres -n ethio-core --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis -n ethio-core --timeout=120s

# Deploy services
kubectl apply -f k8s/identity-deployment.yaml
kubectl apply -f k8s/biometric-deployment.yaml
kubectl apply -f k8s/card-deployment.yaml
kubectl apply -f k8s/transaction-deployment.yaml
kubectl apply -f k8s/security-deployment.yaml
kubectl apply -f k8s/sso-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Check deployment status
kubectl get pods -n ethio-core
kubectl get services -n ethio-core
```

## Production Deployment

### Pre-deployment Checklist

- [ ] All secrets are properly configured
- [ ] Database backups are enabled
- [ ] Monitoring and alerting configured
- [ ] SSL certificates ready
- [ ] DNS records configured
- [ ] Load balancer provisioned
- [ ] Security audit completed

### Environment Configuration

Create production secrets:

```bash
# Create secret from environment file
kubectl create secret generic ethio-secrets \
  --from-env-file=.env.production \
  -n ethio-core
```

### Production Deployment Script

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

NAMESPACE="ethio-core"
REGISTRY=${REGISTRY:-"your-registry.azurecr.io"}
VERSION=${VERSION:-"latest"}

echo "Deploying Ethio-Core version $VERSION to production..."

# Apply namespace and RBAC
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac.yaml

# Apply secrets and configmaps
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# Deploy infrastructure
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/redis-service.yaml

# Wait for infrastructure
echo "Waiting for infrastructure..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s

# Deploy services with rolling update
for service in identity biometric card transaction security sso frontend; do
  echo "Deploying $service service..."
  kubectl set image deployment/${service}-deployment \
    ${service}=${REGISTRY}/ethio-${service}:${VERSION} \
    -n $NAMESPACE
  kubectl rollout status deployment/${service}-deployment -n $NAMESPACE
done

# Apply ingress
kubectl apply -f k8s/ingress.yaml

echo "Deployment complete!"
kubectl get pods -n $NAMESPACE
```

### Rolling Update

```bash
# Update a single service
kubectl set image deployment/identity-deployment \
  identity=your-registry.azurecr.io/ethio-identity:v1.0.1 \
  -n ethio-core

# Watch rollout status
kubectl rollout status deployment/identity-deployment -n ethio-core

# Rollback if needed
kubectl rollout undo deployment/identity-deployment -n ethio-core
```

### Scaling

```bash
# Scale a service
kubectl scale deployment identity-deployment --replicas=3 -n ethio-core

# Auto-scaling (HPA)
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: identity-hpa
  namespace: ethio-core
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: identity-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF
```

## Database Migrations

### Run Migrations

```bash
# Connect to migration pod
kubectl run migrations --rm -it \
  --image=your-registry.azurecr.io/ethio-identity:latest \
  --env="DATABASE_URL=$DATABASE_URL" \
  -n ethio-core \
  -- alembic upgrade head
```

### Backup Database

```bash
# Create backup
kubectl exec -it postgres-0 -n ethio-core -- \
  pg_dump -U ethio ethio_core > backup_$(date +%Y%m%d).sql

# Restore backup
kubectl exec -i postgres-0 -n ethio-core -- \
  psql -U ethio ethio_core < backup_20260324.sql
```

## Monitoring

### Health Checks

Each service exposes health endpoints:

```bash
# Check service health
curl http://localhost:8001/health
curl http://localhost:8001/ready
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Logs

```bash
# View logs for all pods
kubectl logs -l app=identity -n ethio-core --tail=100 -f

# View logs for specific pod
kubectl logs identity-deployment-xxxxx -n ethio-core -f
```

## Troubleshooting

### Common Issues

**Pods not starting:**
```bash
# Check pod events
kubectl describe pod <pod-name> -n ethio-core

# Check resource limits
kubectl top pods -n ethio-core
```

**Database connection issues:**
```bash
# Test database connectivity
kubectl run psql-test --rm -it \
  --image=postgres:15 \
  -n ethio-core \
  -- psql "$DATABASE_URL" -c "SELECT 1"
```

**Service communication issues:**
```bash
# Test service DNS
kubectl run curl-test --rm -it \
  --image=curlimages/curl \
  -n ethio-core \
  -- curl http://identity-service:8000/health
```

## Rollback Procedures

### Quick Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/identity-deployment -n ethio-core

# Rollback to specific revision
kubectl rollout undo deployment/identity-deployment --to-revision=2 -n ethio-core
```

### Full Rollback

```bash
# Save current state
kubectl get deployments -n ethio-core -o yaml > deployments_backup.yaml

# Apply previous version
export VERSION=v0.9.0
./scripts/deploy.sh
```

## Security Considerations

### Secrets Management

- Use Kubernetes secrets or external secret managers (Vault, AWS Secrets Manager)
- Rotate secrets regularly
- Never commit secrets to version control

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: ethio-core
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### Pod Security

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```
