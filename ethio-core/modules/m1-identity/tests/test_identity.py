"""
M1 - Identity Service Tests
Unit and integration tests for the identity service.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid

# Import the app
import sys
sys.path.insert(0, '..')
from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "identity-service"
    
    def test_readiness_check(self, client):
        """Test readiness endpoint returns ready status."""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestUserEndpoints:
    """Test user management endpoints."""
    
    def test_create_user(self, client):
        """Test user creation."""
        user_data = {
            "email": "test@example.com",
            "phone": "+251911234567",
            "full_name": "Test User",
            "password": "SecureP@ssw0rd"
        }
        
        response = client.post("/api/v1/users", json=user_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["status"] == "pending"
        assert data["kyc_level"] == 0
        assert "user_id" in data
    
    def test_create_user_invalid_email(self, client):
        """Test user creation with invalid email fails."""
        user_data = {
            "email": "invalid-email",
            "full_name": "Test User",
            "password": "SecureP@ssw0rd"
        }
        
        response = client.post("/api/v1/users", json=user_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_user(self, client):
        """Test getting user by ID."""
        user_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/users/{user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id


class TestIdentityEndpoints:
    """Test identity verification endpoints."""
    
    def test_get_identity_status(self, client):
        """Test getting identity verification status."""
        user_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/identity/{user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert "kyc_status" in data
        assert "documents" in data
    
    def test_start_kyc_verification(self, client):
        """Test starting KYC verification."""
        kyc_request = {
            "user_id": str(uuid.uuid4()),
            "document_type": "national_id",
            "document_data": {
                "front_image": "base64_encoded_image_data",
                "back_image": "base64_encoded_image_data"
            }
        }
        
        response = client.post("/api/v1/identity/verify", json=kyc_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "verification_id" in data
        assert data["status"] == "pending"
    
    def test_get_verification_status(self, client):
        """Test getting verification status."""
        verification_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/identity/verify/{verification_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["verification_id"] == verification_id
        assert "status" in data


class TestFaydaEndpoints:
    """Test Fayda integration endpoints."""
    
    def test_verify_with_fayda(self, client):
        """Test Fayda verification."""
        fayda_request = {
            "fayda_id": "FID1234567890",
            "consent_token": "valid_consent_token_string",
            "user_data": {
                "full_name": "Test User",
                "date_of_birth": "1990-01-15"
            }
        }
        
        response = client.post("/api/v1/identity/fayda/verify", json=fayda_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "verified" in data
        assert "match_score" in data


class TestInternalEndpoints:
    """Test internal service endpoints."""
    
    def test_get_kyc_level(self, client):
        """Test getting KYC level for internal services."""
        user_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/internal/identity/{user_id}/kyc-level")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert "kyc_level" in data
        assert "is_verified" in data


# Unit tests for components
class TestOCREngine:
    """Test OCR engine functionality."""
    
    @pytest.mark.asyncio
    async def test_process_document(self):
        """Test document OCR processing."""
        from ocr_engine import OCREngine
        
        engine = OCREngine()
        result = await engine.process_document(b"test_content", "national_id")
        
        assert "extracted_data" in result
        assert "confidence_score" in result
        assert result["confidence_score"] > 0
    
    @pytest.mark.asyncio
    async def test_validate_document(self):
        """Test document validation."""
        from ocr_engine import OCREngine
        
        engine = OCREngine()
        result = await engine.validate_document(b"test_content", "national_id")
        
        assert "is_valid" in result
        assert "quality_score" in result


class TestDocumentValidator:
    """Test document validation utilities."""
    
    def test_validate_id_number(self):
        """Test ID number validation."""
        from ocr_engine import DocumentValidator
        
        assert DocumentValidator.validate_id_number("ETH1234567890") == True
        assert DocumentValidator.validate_id_number("123") == False
    
    def test_validate_expiry_date_valid(self):
        """Test expiry date validation with valid date."""
        from ocr_engine import DocumentValidator
        
        assert DocumentValidator.validate_expiry_date("2030-01-15") == True
    
    def test_validate_expiry_date_expired(self):
        """Test expiry date validation with expired date."""
        from ocr_engine import DocumentValidator
        
        assert DocumentValidator.validate_expiry_date("2020-01-15") == False
    
    def test_calculate_age(self):
        """Test age calculation."""
        from ocr_engine import DocumentValidator
        
        age = DocumentValidator.calculate_age("1990-01-15")
        assert age > 30  # Born in 1990


class TestFaydaClient:
    """Test Fayda client functionality."""
    
    @pytest.mark.asyncio
    async def test_verify_valid_id(self):
        """Test verification with valid Fayda ID."""
        from fayda_integration import FaydaClient
        
        client = FaydaClient()
        result = await client.verify(
            fayda_id="FID1234567890",
            consent_token="valid_token_string"
        )
        
        assert result["verified"] == True
        assert "match_score" in result
    
    @pytest.mark.asyncio
    async def test_verify_invalid_id(self):
        """Test verification with invalid Fayda ID."""
        from fayda_integration import FaydaClient
        
        client = FaydaClient()
        result = await client.verify(
            fayda_id="INVALID123",
            consent_token="valid_token_string"
        )
        
        assert result["verified"] == False


class TestEventHandlers:
    """Test event handling functionality."""
    
    @pytest.mark.asyncio
    async def test_publish_event(self):
        """Test event publishing."""
        from event_handlers import EventPublisher
        
        publisher = EventPublisher()
        event_id = await publisher.publish(
            event_type="USER_CREATED",
            aggregate_type="User",
            aggregate_id=str(uuid.uuid4()),
            payload={"email": "test@example.com"}
        )
        
        assert event_id is not None
        assert len(event_id) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
