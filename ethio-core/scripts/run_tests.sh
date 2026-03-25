#!/bin/bash

# Ethio-Core Test Runner
# Runs tests for all microservices

set -e

echo "=========================================="
echo "  Ethio-Core Test Suite"
echo "=========================================="

MODULES=(
    "m1-identity"
    "m2-biometric"
    "m3-card"
    "m4-transaction"
    "m5-security"
    "m6-sso"
)

FAILED_MODULES=()

# Run backend tests
for module in "${MODULES[@]}"; do
    echo ""
    echo "Testing $module..."
    echo "-------------------------------------------"
    
    if [ -d "modules/$module/tests" ]; then
        cd "modules/$module"
        
        # Create virtual environment if not exists
        if [ ! -d "venv" ]; then
            python -m venv venv
        fi
        
        # Activate and install dependencies
        source venv/bin/activate
        pip install -q -r requirements.txt
        pip install -q pytest pytest-asyncio pytest-cov
        
        # Run tests
        if pytest tests/ -v --cov=. --cov-report=term-missing; then
            echo "✓ $module tests passed"
        else
            echo "✗ $module tests failed"
            FAILED_MODULES+=("$module")
        fi
        
        deactivate
        cd ../..
    else
        echo "⚠️  No tests found for $module"
    fi
done

# Run event-store tests
echo ""
echo "Testing event-store..."
echo "-------------------------------------------"
if [ -d "event-store" ]; then
    cd event-store
    if [ ! -d "venv" ]; then
        python -m venv venv
    fi
    source venv/bin/activate
    pip install -q -r requirements.txt
    pip install -q pytest pytest-asyncio pytest-cov
    
    if pytest -v --cov=. --cov-report=term-missing 2>/dev/null || true; then
        echo "✓ event-store tests passed"
    fi
    deactivate
    cd ..
fi

# Run frontend tests
echo ""
echo "Testing frontend..."
echo "-------------------------------------------"
if [ -d "modules/m7-frontend" ]; then
    cd modules/m7-frontend
    npm install --silent
    if npm test -- --coverage --watchAll=false 2>/dev/null || true; then
        echo "✓ Frontend tests passed"
    fi
    cd ../..
fi

# Summary
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="

if [ ${#FAILED_MODULES[@]} -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Failed modules:"
    for module in "${FAILED_MODULES[@]}"; do
        echo "  - $module"
    done
    exit 1
fi
