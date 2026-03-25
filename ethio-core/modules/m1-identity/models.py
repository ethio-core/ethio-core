"""
M1 - Identity Service Models
Pydantic models for request/response validation and data structures.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class UserStatus(str, Enum):
    """User account status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class KYCStatus(str, Enum):
    """KYC verification status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DocumentType(str, Enum):
    """Supported identity document types."""
    NATIONAL_ID = "national_id"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    RESIDENCE_PERMIT = "residence_permit"


# Base Models
class User(BaseModel):
    """User domain model."""
    id: str
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    status: UserStatus = UserStatus.PENDING
    kyc_level: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class IdentityDocument(BaseModel):
    """Identity document model."""
    id: str
    user_id: str
    document_type: DocumentType
    document_number: Optional[str] = None
    issuing_country: str = "ETH"
    expiry_date: Optional[datetime] = None
    verification_status: KYCStatus = KYCStatus.PENDING
    ocr_data: Optional[Dict[str, Any]] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        use_enum_values = True


class KYCVerification(BaseModel):
    """KYC verification record model."""
    id: str
    user_id: str
    verification_type: str
    status: KYCStatus = KYCStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    risk_score: Optional[float] = None
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        use_enum_values = True


# Request Models
class UserCreate(BaseModel):
    """Request model for creating a new user."""
    email: EmailStr = Field(..., description="User's email address")
    phone: Optional[str] = Field(None, description="User's phone number in E.164 format")
    full_name: str = Field(..., min_length=2, max_length=255, description="User's full name")
    password: str = Field(..., min_length=8, description="User's password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "phone": "+251911234567",
                "full_name": "John Doe",
                "password": "SecureP@ssw0rd"
            }
        }


class UserUpdate(BaseModel):
    """Request model for updating user information."""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)


class DocumentData(BaseModel):
    """Document data for KYC verification."""
    front_image: str = Field(..., description="Base64 encoded front image of document")
    back_image: Optional[str] = Field(None, description="Base64 encoded back image of document")


class KYCRequest(BaseModel):
    """Request model for initiating KYC verification."""
    user_id: str = Field(..., description="User ID to verify")
    document_type: DocumentType = Field(..., description="Type of identity document")
    document_data: DocumentData = Field(..., description="Document images")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_type": "national_id",
                "document_data": {
                    "front_image": "base64_encoded_image_data",
                    "back_image": "base64_encoded_image_data"
                }
            }
        }


class OCRRequest(BaseModel):
    """Request model for OCR processing."""
    document_image: str = Field(..., description="Base64 encoded document image")
    document_type: DocumentType = Field(..., description="Type of document to process")


class FaydaVerificationRequest(BaseModel):
    """Request model for Fayda verification."""
    fayda_id: str = Field(..., description="Fayda (National ID) number")
    consent_token: str = Field(..., description="User consent token for data access")
    user_data: Optional[Dict[str, Any]] = Field(None, description="User data to verify against")

    class Config:
        json_schema_extra = {
            "example": {
                "fayda_id": "FID1234567890",
                "consent_token": "consent_token_string",
                "user_data": {
                    "full_name": "John Doe",
                    "date_of_birth": "1990-01-15"
                }
            }
        }


# Response Models
class UserResponse(BaseModel):
    """Response model for user data."""
    user_id: str
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    status: str
    kyc_level: int
    created_at: datetime


class KYCResponse(BaseModel):
    """Response model for KYC verification initiation."""
    verification_id: str
    status: str
    created_at: datetime


class OCRResponse(BaseModel):
    """Response model for OCR processing."""
    ocr_id: str
    extracted_data: Dict[str, Any]
    confidence_score: float


class FaydaVerificationResponse(BaseModel):
    """Response model for Fayda verification."""
    verified: bool
    match_score: float
    details: Dict[str, Any]


class IdentityStatusResponse(BaseModel):
    """Response model for identity status check."""
    user_id: str
    kyc_status: str
    verification_level: int
    verified_at: Optional[datetime] = None
    documents: List[Dict[str, Any]]


# Event Models
class DomainEvent(BaseModel):
    """Base model for domain events."""
    id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = {}
    version: int = 1
    created_at: datetime


class UserCreatedEvent(DomainEvent):
    """Event emitted when a user is created."""
    event_type: str = "USER_CREATED"
    aggregate_type: str = "User"


class KYCInitiatedEvent(DomainEvent):
    """Event emitted when KYC verification is initiated."""
    event_type: str = "KYC_INITIATED"
    aggregate_type: str = "KYCVerification"


class KYCVerifiedEvent(DomainEvent):
    """Event emitted when KYC verification is completed successfully."""
    event_type: str = "KYC_VERIFIED"
    aggregate_type: str = "KYCVerification"


class KYCRejectedEvent(DomainEvent):
    """Event emitted when KYC verification is rejected."""
    event_type: str = "KYC_REJECTED"
    aggregate_type: str = "KYCVerification"
