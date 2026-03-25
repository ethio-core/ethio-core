"""
M1 - Identity Service
FastAPI service for identity management, KYC verification, and document processing.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
import uuid
import os

from models import (
    User, KYCVerification, IdentityDocument, 
    UserCreate, UserResponse, KYCRequest, KYCResponse,
    OCRRequest, OCRResponse, FaydaVerificationRequest, FaydaVerificationResponse
)
from event_handlers import EventPublisher
from ocr_engine import OCREngine
from fayda_integration import FaydaClient
from kyc_orchestrator import KYCOrchestrator

# Initialize FastAPI app
app = FastAPI(
    title="Ethio-Core Identity Service",
    description="Identity management, KYC verification, and document processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
event_publisher = EventPublisher()
ocr_engine = OCREngine()
fayda_client = FaydaClient()
kyc_orchestrator = KYCOrchestrator(event_publisher, ocr_engine, fayda_client)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {"status": "healthy", "service": "identity-service", "timestamp": datetime.utcnow().isoformat()}


@app.get("/ready")
async def readiness_check():
    """Service readiness check endpoint."""
    # Check database and dependencies
    return {"status": "ready", "service": "identity-service"}


# User Management Endpoints
@app.post("/api/v1/users", response_model=UserResponse, status_code=201)
async def create_user(user_data: UserCreate, background_tasks: BackgroundTasks):
    """
    Create a new user account.
    Emits USER_CREATED event on success.
    """
    user_id = str(uuid.uuid4())
    
    # Create user (in production, this would save to database)
    user = User(
        id=user_id,
        email=user_data.email,
        phone=user_data.phone,
        full_name=user_data.full_name,
        status="pending",
        kyc_level=0,
        created_at=datetime.utcnow()
    )
    
    # Publish event asynchronously
    background_tasks.add_task(
        event_publisher.publish,
        "USER_CREATED",
        "User",
        user_id,
        {
            "user_id": user_id,
            "email": user_data.email,
            "phone": user_data.phone,
            "full_name": user_data.full_name,
            "created_at": datetime.utcnow().isoformat()
        }
    )
    
    return UserResponse(
        user_id=user_id,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        status=user.status,
        kyc_level=user.kyc_level,
        created_at=user.created_at
    )


@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user details by ID."""
    # In production, fetch from database
    # For demo, return mock data
    return UserResponse(
        user_id=user_id,
        email="user@example.com",
        phone="+251911234567",
        full_name="John Doe",
        status="active",
        kyc_level=2,
        created_at=datetime.utcnow()
    )


@app.get("/api/v1/identity/{user_id}")
async def get_identity_status(user_id: str):
    """
    Get identity verification status for a user.
    Returns KYC status and verified documents.
    """
    # In production, fetch from database
    return {
        "user_id": user_id,
        "kyc_status": "verified",
        "verification_level": 3,
        "verified_at": datetime.utcnow().isoformat(),
        "documents": [
            {
                "type": "national_id",
                "status": "verified",
                "verified_at": datetime.utcnow().isoformat()
            }
        ]
    }


# KYC Verification Endpoints
@app.post("/api/v1/identity/verify", response_model=KYCResponse)
async def start_kyc_verification(
    kyc_request: KYCRequest, 
    background_tasks: BackgroundTasks
):
    """
    Initiate KYC verification process.
    Orchestrates document verification, OCR, and identity checks.
    """
    verification_id = str(uuid.uuid4())
    
    # Start KYC orchestration
    result = await kyc_orchestrator.start_verification(
        verification_id=verification_id,
        user_id=kyc_request.user_id,
        document_type=kyc_request.document_type,
        document_data=kyc_request.document_data
    )
    
    # Publish KYC_INITIATED event
    background_tasks.add_task(
        event_publisher.publish,
        "KYC_INITIATED",
        "KYCVerification",
        verification_id,
        {
            "verification_id": verification_id,
            "user_id": kyc_request.user_id,
            "verification_type": "document_verification",
            "document_type": kyc_request.document_type,
            "initiated_at": datetime.utcnow().isoformat()
        }
    )
    
    return KYCResponse(
        verification_id=verification_id,
        status="pending",
        created_at=datetime.utcnow()
    )


@app.get("/api/v1/identity/verify/{verification_id}")
async def get_verification_status(verification_id: str):
    """Get the status of a KYC verification request."""
    # In production, fetch from database
    return {
        "verification_id": verification_id,
        "status": "in_progress",
        "steps_completed": ["document_upload", "ocr_processing"],
        "steps_pending": ["fayda_verification", "manual_review"],
        "created_at": datetime.utcnow().isoformat()
    }


# OCR Endpoints
@app.post("/api/v1/identity/ocr", response_model=OCRResponse)
async def process_document_ocr(
    document: UploadFile = File(...),
    document_type: str = "national_id",
    background_tasks: BackgroundTasks = None
):
    """
    Process document using OCR engine.
    Extracts text and structured data from identity documents.
    """
    ocr_id = str(uuid.uuid4())
    
    # Read document content
    content = await document.read()
    
    # Process with OCR engine
    result = await ocr_engine.process_document(content, document_type)
    
    # Publish event
    if background_tasks:
        background_tasks.add_task(
            event_publisher.publish,
            "DOCUMENT_OCR_COMPLETED",
            "Document",
            ocr_id,
            {
                "document_id": ocr_id,
                "document_type": document_type,
                "extracted_data": result["extracted_data"],
                "confidence_score": result["confidence_score"],
                "processed_at": datetime.utcnow().isoformat()
            }
        )
    
    return OCRResponse(
        ocr_id=ocr_id,
        extracted_data=result["extracted_data"],
        confidence_score=result["confidence_score"]
    )


# Fayda Integration Endpoints
@app.post("/api/v1/identity/fayda/verify", response_model=FaydaVerificationResponse)
async def verify_with_fayda(
    request: FaydaVerificationRequest,
    background_tasks: BackgroundTasks
):
    """
    Verify identity using Fayda (Ethiopia National ID system).
    Compares user data with national database.
    """
    verification_id = str(uuid.uuid4())
    
    # Call Fayda API (mocked)
    result = await fayda_client.verify(
        fayda_id=request.fayda_id,
        consent_token=request.consent_token,
        user_data=request.user_data
    )
    
    # Publish event
    background_tasks.add_task(
        event_publisher.publish,
        "FAYDA_VERIFICATION_COMPLETED",
        "FaydaVerification",
        verification_id,
        {
            "verification_id": verification_id,
            "fayda_id": request.fayda_id,
            "is_verified": result["verified"],
            "match_details": result["match_details"],
            "verified_at": datetime.utcnow().isoformat()
        }
    )
    
    return FaydaVerificationResponse(
        verified=result["verified"],
        match_score=result["match_score"],
        details=result["match_details"]
    )


# Internal API for other services
@app.get("/api/v1/internal/identity/{user_id}/kyc-level")
async def get_kyc_level(user_id: str):
    """
    Internal endpoint for other services to check KYC level.
    Used by Card and Transaction services.
    """
    # In production, fetch from database
    return {
        "user_id": user_id,
        "kyc_level": 3,
        "is_verified": True
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
