#!/bin/bash

# Ethio-Core Deployment Script
# Deploys to Kubernetes cluster

set -e

ENVIRONMENT=${1:-staging}
REGISTRY=${DOCKER_REGISTRY:-ghcr.io/ethio-core}
TAG=${IMAGE_TAG:-latest}

echo "=========================================="
echo "  Ethio-Core Deployment"
echo "  Environment: $ENVIRONMENT"
echo "  Registry: $REGISTRY"
echo "  Tag: $TAG"
echo "=========================================="

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "Error: Invalid environment. Use 'staging' or 'production'"
    exit 1
fi

# Check kubectl
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required but not installed. Aborting." >&2; exit 1; }

# Build and push images
echo ""
echo "Building and pushing Docker images..."

SERVICES=(
    "m1-identity:modules/m1-identity"
    "m2-biometric:modules/m2-biometric"
    "m3-card:modules/m3-card"
    "m4-transaction:modules/m4-transaction"
    "m5-security:modules/m5-security"
    "m6-sso:modules/m6-sso"
    "m7-frontend:modules/m7-frontend"
    "event-store:event-store"
)

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name path <<< "$service"
    echo "Building $name..."
    docker build -t "$REGISTRY/$name:$TAG" "$path"
    docker push "$REGISTRY/$name:$TAG"
done

# Apply Kubernetes configs
echo ""
echo "Applying Kubernetes configurations..."

# Apply base configurations
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/secrets.yaml

# Apply service deployments
for file in k8s/services/*.yaml; do
    echo "Applying $file..."
    kubectl apply -f "$file"
done

# Apply ingress
kubectl apply -f k8s/base/ingress.yaml

# Wait for deployments
echo ""
echo "Waiting for deployments to be ready..."

DEPLOYMENTS=(
    "identity-service"
    "biometric-service"
    "card-service"
    "transaction-service"
    "security-service"
    "sso-service"
    "frontend-service"
)

NAMESPACE="ethio-core"
if [ "$ENVIRONMENT" == "staging" ]; then
    NAMESPACE="ethio-core-staging"
fi

for deployment in "${DEPLOYMENTS[@]}"; do
    echo "Waiting for $deployment..."
    kubectl -n "$NAMESPACE" rollout status deployment/"$deployment" --timeout=300s
done

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Services are running in namespace: $NAMESPACE"
echo ""
echo "To check status, run:"
echo "  kubectl -n $NAMESPACE get pods"
echo "  kubectl -n $NAMESPACE get services"
echo ""
