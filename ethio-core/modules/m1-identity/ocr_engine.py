"""
M1 - Identity Service OCR Engine
Mock OCR engine for document processing.
In production, integrate with actual OCR service (e.g., AWS Textract, Google Vision).
"""

import os
import base64
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OCREngine:
    """
    OCR Engine for extracting text and structured data from identity documents.
    
    This is a mock implementation. In production, integrate with:
    - AWS Textract
    - Google Cloud Vision
    - Azure Computer Vision
    - Custom ML models
    """
    
    def __init__(self):
        self.ocr_service_url = os.getenv("OCR_SERVICE_URL", "http://localhost:8010")
        self.api_key = os.getenv("OCR_API_KEY")
        
        # Document type configurations
        self.document_configs = {
            "national_id": {
                "fields": ["full_name", "id_number", "date_of_birth", "gender", "expiry_date", "address"],
                "mrz_enabled": True
            },
            "passport": {
                "fields": ["full_name", "passport_number", "nationality", "date_of_birth", "expiry_date", "gender"],
                "mrz_enabled": True
            },
            "drivers_license": {
                "fields": ["full_name", "license_number", "date_of_birth", "expiry_date", "categories", "address"],
                "mrz_enabled": False
            }
        }
    
    async def process_document(
        self,
        document_content: bytes,
        document_type: str
    ) -> Dict[str, Any]:
        """
        Process a document image and extract structured data.
        
        Args:
            document_content: Raw bytes of the document image
            document_type: Type of document (national_id, passport, etc.)
            
        Returns:
            Dictionary with extracted data and confidence scores
        """
        logger.info(f"Processing {document_type} document")
        
        # Validate document type
        if document_type not in self.document_configs:
            raise ValueError(f"Unsupported document type: {document_type}")
        
        # Generate document hash for deduplication
        doc_hash = hashlib.sha256(document_content).hexdigest()
        logger.debug(f"Document hash: {doc_hash}")
        
        # Mock OCR processing - in production, call actual OCR service
        extracted_data = await self._mock_extract_data(document_type)
        
        # Calculate overall confidence score
        confidence_score = self._calculate_confidence(extracted_data)
        
        return {
            "document_hash": doc_hash,
            "document_type": document_type,
            "extracted_data": extracted_data,
            "confidence_score": confidence_score,
            "processing_time_ms": random.randint(500, 2000),
            "processed_at": datetime.utcnow().isoformat()
        }
    
    async def _mock_extract_data(self, document_type: str) -> Dict[str, Any]:
        """
        Mock data extraction based on document type.
        In production, this would parse actual OCR results.
        """
        if document_type == "national_id":
            return {
                "full_name": "Abebe Kebede",
                "id_number": f"ETH{random.randint(100000000, 999999999)}",
                "date_of_birth": "1990-05-15",
                "gender": "Male",
                "expiry_date": "2030-05-15",
                "address": "Addis Ababa, Ethiopia",
                "issuing_authority": "NIDP",
                "issue_date": "2020-05-15"
            }
        elif document_type == "passport":
            return {
                "full_name": "Abebe Kebede",
                "passport_number": f"EP{random.randint(1000000, 9999999)}",
                "nationality": "Ethiopian",
                "date_of_birth": "1990-05-15",
                "expiry_date": "2030-05-15",
                "gender": "M",
                "place_of_birth": "Addis Ababa",
                "mrz_line1": "P<ETHKEBEDE<<ABEBE<<<<<<<<<<<<<<<<<<<<<<<<<<",
                "mrz_line2": f"EP{random.randint(1000000, 9999999)}<6ETH9005155M3005159<<<<<<<<<<<<<<00"
            }
        else:
            return {
                "full_name": "Abebe Kebede",
                "license_number": f"DL{random.randint(100000, 999999)}",
                "date_of_birth": "1990-05-15",
                "expiry_date": "2028-05-15",
                "categories": ["B", "C"],
                "address": "Addis Ababa, Ethiopia"
            }
    
    def _calculate_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """
        Calculate overall confidence score based on extracted fields.
        """
        # Mock confidence calculation
        # In production, aggregate individual field confidences
        base_confidence = 0.85
        field_count = len(extracted_data)
        
        # Adjust confidence based on field completeness
        if field_count >= 6:
            base_confidence += 0.10
        elif field_count >= 4:
            base_confidence += 0.05
            
        return min(base_confidence + random.uniform(-0.05, 0.05), 0.99)
    
    async def validate_document(
        self,
        document_content: bytes,
        document_type: str
    ) -> Dict[str, Any]:
        """
        Validate document authenticity and quality.
        
        Checks:
        - Image quality (resolution, blur, lighting)
        - Document completeness (all corners visible)
        - Tampering detection
        - MRZ validation (if applicable)
        """
        logger.info(f"Validating {document_type} document")
        
        # Mock validation - in production, run actual checks
        return {
            "is_valid": True,
            "quality_score": random.uniform(0.8, 0.99),
            "checks": {
                "image_quality": {"passed": True, "score": 0.92},
                "document_completeness": {"passed": True, "score": 0.95},
                "tampering_detection": {"passed": True, "confidence": 0.88},
                "blur_detection": {"passed": True, "blur_score": 0.15}
            },
            "warnings": []
        }
    
    async def extract_face_from_document(
        self,
        document_content: bytes
    ) -> Optional[bytes]:
        """
        Extract face photo from identity document.
        Used for face matching with selfie.
        """
        logger.info("Extracting face from document")
        
        # Mock implementation - in production, use face detection
        # Return extracted face image bytes
        return None
    
    async def parse_mrz(self, mrz_text: str) -> Dict[str, Any]:
        """
        Parse Machine Readable Zone (MRZ) from passport or ID.
        
        MRZ contains structured data that can validate extracted OCR data.
        """
        logger.info("Parsing MRZ")
        
        # Mock MRZ parsing
        # In production, use proper MRZ parsing library
        return {
            "document_type": "P",
            "country_code": "ETH",
            "surname": "KEBEDE",
            "given_names": "ABEBE",
            "document_number": "EP1234567",
            "nationality": "ETH",
            "date_of_birth": "900515",
            "sex": "M",
            "expiry_date": "300515",
            "check_digits_valid": True
        }


class DocumentValidator:
    """
    Additional document validation utilities.
    """
    
    @staticmethod
    def validate_id_number(id_number: str, country: str = "ETH") -> bool:
        """Validate ID number format based on country."""
        if country == "ETH":
            # Ethiopian ID format validation
            return len(id_number) >= 10
        return True
    
    @staticmethod
    def validate_expiry_date(expiry_date: str) -> bool:
        """Check if document is not expired."""
        try:
            expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            return expiry > date.today()
        except ValueError:
            return False
    
    @staticmethod
    def calculate_age(date_of_birth: str) -> int:
        """Calculate age from date of birth."""
        try:
            dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            today = date.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except ValueError:
            return 0
