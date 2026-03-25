"""
M1 - Identity Service KYC Orchestrator
Orchestrates the KYC verification workflow including document processing,
OCR, biometric verification, and Fayda integration.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid

from event_handlers import EventPublisher
from ocr_engine import OCREngine, DocumentValidator
from fayda_integration import FaydaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KYCStep(str, Enum):
    """KYC verification steps."""
    DOCUMENT_UPLOAD = "document_upload"
    OCR_PROCESSING = "ocr_processing"
    DOCUMENT_VALIDATION = "document_validation"
    FAYDA_VERIFICATION = "fayda_verification"
    BIOMETRIC_CHECK = "biometric_check"
    RISK_ASSESSMENT = "risk_assessment"
    MANUAL_REVIEW = "manual_review"
    COMPLETED = "completed"


class KYCLevel(int, Enum):
    """KYC verification levels."""
    LEVEL_0 = 0  # Unverified
    LEVEL_1 = 1  # Basic (email + phone)
    LEVEL_2 = 2  # Standard (document verified)
    LEVEL_3 = 3  # Full (document + Fayda + biometric)


class KYCOrchestrator:
    """
    Orchestrates the complete KYC verification workflow.
    
    Flow:
    1. Document upload and quality check
    2. OCR processing to extract data
    3. Document validation (expiry, format)
    4. Fayda verification (optional, for Level 3)
    5. Biometric check (optional, for Level 3)
    6. Risk assessment
    7. Manual review (if required)
    8. Final decision
    """
    
    def __init__(
        self,
        event_publisher: EventPublisher,
        ocr_engine: OCREngine,
        fayda_client: FaydaClient
    ):
        self.event_publisher = event_publisher
        self.ocr_engine = ocr_engine
        self.fayda_client = fayda_client
        self.document_validator = DocumentValidator()
        
        # Configuration
        self.auto_approve_threshold = float(os.getenv("KYC_AUTO_APPROVE_THRESHOLD", "0.90"))
        self.manual_review_threshold = float(os.getenv("KYC_MANUAL_REVIEW_THRESHOLD", "0.70"))
        
    async def start_verification(
        self,
        verification_id: str,
        user_id: str,
        document_type: str,
        document_data: Any,
        verification_level: KYCLevel = KYCLevel.LEVEL_2
    ) -> Dict[str, Any]:
        """
        Start a new KYC verification process.
        
        Args:
            verification_id: Unique verification ID
            user_id: User being verified
            document_type: Type of document submitted
            document_data: Document images/data
            verification_level: Target verification level
            
        Returns:
            Verification initiation result
        """
        logger.info(f"Starting KYC verification {verification_id} for user {user_id}")
        
        # Initialize verification state
        state = KYCVerificationState(
            verification_id=verification_id,
            user_id=user_id,
            document_type=document_type,
            target_level=verification_level
        )
        
        # Process document asynchronously
        asyncio.create_task(self._run_verification_pipeline(state, document_data))
        
        return {
            "verification_id": verification_id,
            "status": "initiated",
            "target_level": verification_level.value,
            "started_at": datetime.utcnow().isoformat()
        }
    
    async def _run_verification_pipeline(
        self,
        state: "KYCVerificationState",
        document_data: Any
    ) -> None:
        """
        Run the full KYC verification pipeline.
        """
        try:
            # Step 1: Document quality check
            state.current_step = KYCStep.DOCUMENT_UPLOAD
            quality_result = await self._check_document_quality(document_data)
            state.add_step_result(KYCStep.DOCUMENT_UPLOAD, quality_result)
            
            if not quality_result["passed"]:
                await self._fail_verification(state, "Document quality check failed")
                return
            
            # Step 2: OCR Processing
            state.current_step = KYCStep.OCR_PROCESSING
            ocr_result = await self._process_ocr(document_data, state.document_type)
            state.add_step_result(KYCStep.OCR_PROCESSING, ocr_result)
            state.extracted_data = ocr_result.get("extracted_data", {})
            
            # Step 3: Document Validation
            state.current_step = KYCStep.DOCUMENT_VALIDATION
            validation_result = await self._validate_document(state.extracted_data)
            state.add_step_result(KYCStep.DOCUMENT_VALIDATION, validation_result)
            
            if not validation_result["is_valid"]:
                await self._fail_verification(state, validation_result.get("reason", "Document validation failed"))
                return
            
            # Step 4: Fayda Verification (for Level 3)
            if state.target_level == KYCLevel.LEVEL_3:
                state.current_step = KYCStep.FAYDA_VERIFICATION
                fayda_result = await self._verify_with_fayda(state)
                state.add_step_result(KYCStep.FAYDA_VERIFICATION, fayda_result)
                
                if not fayda_result.get("verified"):
                    await self._fail_verification(state, "Fayda verification failed")
                    return
            
            # Step 5: Risk Assessment
            state.current_step = KYCStep.RISK_ASSESSMENT
            risk_result = await self._assess_risk(state)
            state.add_step_result(KYCStep.RISK_ASSESSMENT, risk_result)
            state.risk_score = risk_result["risk_score"]
            
            # Step 6: Decision
            await self._make_decision(state)
            
        except Exception as e:
            logger.error(f"KYC verification error: {str(e)}")
            await self._fail_verification(state, f"Verification error: {str(e)}")
    
    async def _check_document_quality(self, document_data: Any) -> Dict[str, Any]:
        """Check document image quality."""
        logger.info("Checking document quality")
        
        # Mock quality check - in production, analyze image
        return {
            "passed": True,
            "quality_score": 0.92,
            "checks": {
                "resolution": "pass",
                "blur": "pass",
                "lighting": "pass",
                "corners_visible": "pass"
            }
        }
    
    async def _process_ocr(self, document_data: Any, document_type: str) -> Dict[str, Any]:
        """Process document with OCR engine."""
        logger.info(f"Processing OCR for {document_type}")
        
        # Convert document data to bytes if needed
        if hasattr(document_data, "front_image"):
            content = document_data.front_image.encode() if isinstance(document_data.front_image, str) else document_data.front_image
        else:
            content = b"mock_document_content"
        
        result = await self.ocr_engine.process_document(content, document_type)
        return result
    
    async def _validate_document(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted document data."""
        logger.info("Validating document data")
        
        issues = []
        
        # Check ID number format
        id_number = extracted_data.get("id_number", "")
        if not self.document_validator.validate_id_number(id_number):
            issues.append("Invalid ID number format")
        
        # Check expiry date
        expiry_date = extracted_data.get("expiry_date", "")
        if expiry_date and not self.document_validator.validate_expiry_date(expiry_date):
            issues.append("Document has expired")
        
        # Check age (must be 18+)
        dob = extracted_data.get("date_of_birth", "")
        if dob:
            age = self.document_validator.calculate_age(dob)
            if age < 18:
                issues.append("User must be at least 18 years old")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "reason": issues[0] if issues else None
        }
    
    async def _verify_with_fayda(self, state: "KYCVerificationState") -> Dict[str, Any]:
        """Verify user data with Fayda."""
        logger.info("Verifying with Fayda")
        
        # Mock Fayda verification
        fayda_id = state.extracted_data.get("id_number", "")
        
        result = await self.fayda_client.verify(
            fayda_id=fayda_id,
            consent_token="mock_consent_token",
            user_data={
                "full_name": state.extracted_data.get("full_name"),
                "date_of_birth": state.extracted_data.get("date_of_birth")
            }
        )
        
        return result
    
    async def _assess_risk(self, state: "KYCVerificationState") -> Dict[str, Any]:
        """Perform risk assessment based on verification results."""
        logger.info("Assessing risk")
        
        risk_factors = []
        risk_score = 0.0
        
        # Check OCR confidence
        ocr_confidence = state.step_results.get(KYCStep.OCR_PROCESSING, {}).get("confidence_score", 0)
        if ocr_confidence < 0.80:
            risk_factors.append("Low OCR confidence")
            risk_score += 0.2
        
        # Check Fayda match score (if applicable)
        fayda_result = state.step_results.get(KYCStep.FAYDA_VERIFICATION, {})
        if fayda_result:
            match_score = fayda_result.get("match_score", 0)
            if match_score < 0.90:
                risk_factors.append("Fayda match score below threshold")
                risk_score += 0.3
        
        # Normalize risk score (0 = low risk, 1 = high risk)
        risk_score = min(risk_score, 1.0)
        
        return {
            "risk_score": risk_score,
            "risk_level": "low" if risk_score < 0.3 else "medium" if risk_score < 0.6 else "high",
            "risk_factors": risk_factors
        }
    
    async def _make_decision(self, state: "KYCVerificationState") -> None:
        """Make final verification decision."""
        logger.info(f"Making decision for verification {state.verification_id}")
        
        # Calculate overall score
        ocr_confidence = state.step_results.get(KYCStep.OCR_PROCESSING, {}).get("confidence_score", 0)
        risk_score = state.risk_score or 0
        
        overall_score = ocr_confidence * (1 - risk_score)
        
        if overall_score >= self.auto_approve_threshold:
            # Auto-approve
            await self._approve_verification(state)
        elif overall_score >= self.manual_review_threshold:
            # Queue for manual review
            await self._queue_for_review(state)
        else:
            # Auto-reject
            await self._fail_verification(state, "Verification score below threshold")
    
    async def _approve_verification(self, state: "KYCVerificationState") -> None:
        """Approve the verification."""
        logger.info(f"Approving verification {state.verification_id}")
        
        state.status = "approved"
        state.completed_at = datetime.utcnow()
        
        # Publish KYC_VERIFIED event
        await self.event_publisher.publish(
            "KYC_VERIFIED",
            "KYCVerification",
            state.verification_id,
            {
                "verification_id": state.verification_id,
                "user_id": state.user_id,
                "kyc_level": state.target_level.value,
                "verified_at": state.completed_at.isoformat()
            }
        )
    
    async def _fail_verification(self, state: "KYCVerificationState", reason: str) -> None:
        """Fail the verification."""
        logger.info(f"Failing verification {state.verification_id}: {reason}")
        
        state.status = "rejected"
        state.rejection_reason = reason
        state.completed_at = datetime.utcnow()
        
        # Publish KYC_REJECTED event
        await self.event_publisher.publish(
            "KYC_REJECTED",
            "KYCVerification",
            state.verification_id,
            {
                "verification_id": state.verification_id,
                "user_id": state.user_id,
                "rejection_reason": reason,
                "rejected_at": state.completed_at.isoformat()
            }
        )
    
    async def _queue_for_review(self, state: "KYCVerificationState") -> None:
        """Queue verification for manual review."""
        logger.info(f"Queuing verification {state.verification_id} for manual review")
        
        state.status = "pending_review"
        state.current_step = KYCStep.MANUAL_REVIEW


class KYCVerificationState:
    """
    Holds the state of a KYC verification process.
    """
    
    def __init__(
        self,
        verification_id: str,
        user_id: str,
        document_type: str,
        target_level: KYCLevel
    ):
        self.verification_id = verification_id
        self.user_id = user_id
        self.document_type = document_type
        self.target_level = target_level
        
        self.status = "in_progress"
        self.current_step = KYCStep.DOCUMENT_UPLOAD
        self.step_results: Dict[KYCStep, Dict[str, Any]] = {}
        self.extracted_data: Dict[str, Any] = {}
        self.risk_score: Optional[float] = None
        self.rejection_reason: Optional[str] = None
        
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
    
    def add_step_result(self, step: KYCStep, result: Dict[str, Any]) -> None:
        """Add result for a completed step."""
        self.step_results[step] = {
            **result,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "verification_id": self.verification_id,
            "user_id": self.user_id,
            "document_type": self.document_type,
            "target_level": self.target_level.value,
            "status": self.status,
            "current_step": self.current_step.value,
            "step_results": {k.value: v for k, v in self.step_results.items()},
            "risk_score": self.risk_score,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
