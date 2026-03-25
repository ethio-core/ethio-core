"""
M1 - Identity Service Fayda Integration
Integration with Ethiopia's National Digital ID (Fayda) system.
This is a mock implementation for development/hackathon purposes.
"""

import os
import logging
import hashlib
import hmac
from typing import Dict, Any, Optional
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FaydaClient:
    """
    Client for interacting with Fayda (Ethiopia National ID) API.
    
    Fayda is Ethiopia's national digital identity system that provides:
    - Identity verification
    - Biometric matching
    - Demographic data validation
    
    This is a mock implementation. In production, integrate with actual Fayda API.
    """
    
    def __init__(self):
        self.api_url = os.getenv("FAYDA_API_URL", "https://api.fayda.et")
        self.api_key = os.getenv("FAYDA_API_KEY")
        self.client_id = os.getenv("FAYDA_CLIENT_ID")
        self.client_secret = os.getenv("FAYDA_CLIENT_SECRET")
        
    async def verify(
        self,
        fayda_id: str,
        consent_token: str,
        user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verify user identity against Fayda database.
        
        Args:
            fayda_id: User's Fayda ID number
            consent_token: Token proving user consent for data access
            user_data: Optional user data to verify against
            
        Returns:
            Verification result with match details
        """
        logger.info(f"Verifying Fayda ID: {fayda_id[:4]}****")
        
        # Validate consent token
        if not self._validate_consent(consent_token):
            return {
                "verified": False,
                "error": "invalid_consent",
                "message": "Consent token is invalid or expired"
            }
        
        # Mock Fayda API call
        fayda_data = await self._fetch_fayda_data(fayda_id)
        
        if fayda_data is None:
            return {
                "verified": False,
                "error": "not_found",
                "message": "Fayda ID not found in database"
            }
        
        # Perform matching if user data provided
        if user_data:
            match_result = self._match_user_data(user_data, fayda_data)
            return {
                "verified": match_result["is_match"],
                "match_score": match_result["overall_score"],
                "match_details": match_result["details"]
            }
        
        # Return verification without matching
        return {
            "verified": True,
            "match_score": 1.0,
            "match_details": {
                "fayda_id_valid": True,
                "account_active": True
            }
        }
    
    async def get_demographics(
        self,
        fayda_id: str,
        consent_token: str,
        fields: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Retrieve demographic data from Fayda.
        
        Args:
            fayda_id: User's Fayda ID
            consent_token: Consent token for data access
            fields: Specific fields to retrieve (None = all)
            
        Returns:
            Demographic data based on consent scope
        """
        logger.info(f"Fetching demographics for Fayda ID: {fayda_id[:4]}****")
        
        if not self._validate_consent(consent_token):
            raise ValueError("Invalid consent token")
        
        # Mock demographic data
        demographics = {
            "full_name": "Abebe Kebede",
            "date_of_birth": "1990-05-15",
            "gender": "Male",
            "address": {
                "region": "Addis Ababa",
                "zone": "Yeka",
                "woreda": "07",
                "kebele": "03"
            },
            "photo_available": True
        }
        
        # Filter fields if specified
        if fields:
            demographics = {k: v for k, v in demographics.items() if k in fields}
        
        return demographics
    
    async def verify_biometric(
        self,
        fayda_id: str,
        consent_token: str,
        biometric_data: bytes,
        biometric_type: str = "face"
    ) -> Dict[str, Any]:
        """
        Verify biometric data against Fayda records.
        
        Args:
            fayda_id: User's Fayda ID
            consent_token: Consent token
            biometric_data: Biometric template or image
            biometric_type: Type of biometric (face, fingerprint)
            
        Returns:
            Biometric match result
        """
        logger.info(f"Verifying {biometric_type} biometric against Fayda")
        
        if not self._validate_consent(consent_token):
            raise ValueError("Invalid consent token")
        
        # Mock biometric verification
        match_score = random.uniform(0.85, 0.99)
        
        return {
            "is_match": match_score > 0.80,
            "match_score": match_score,
            "biometric_type": biometric_type,
            "quality_score": random.uniform(0.70, 0.95),
            "verified_at": datetime.utcnow().isoformat()
        }
    
    async def _fetch_fayda_data(self, fayda_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from Fayda API.
        Mock implementation returns sample data.
        """
        # Simulate API latency
        # In production, make actual HTTP request to Fayda API
        
        # Mock data - return None for specific test IDs
        if fayda_id.startswith("INVALID"):
            return None
        
        return {
            "fayda_id": fayda_id,
            "full_name": "Abebe Kebede",
            "date_of_birth": "1990-05-15",
            "gender": "Male",
            "nationality": "Ethiopian",
            "region": "Addis Ababa",
            "status": "active",
            "registered_at": "2020-01-15"
        }
    
    def _validate_consent(self, consent_token: str) -> bool:
        """
        Validate consent token.
        In production, verify signature and expiration.
        """
        if not consent_token:
            return False
        
        # Mock validation - in production, verify JWT or signed token
        return len(consent_token) > 10
    
    def _match_user_data(
        self,
        user_data: Dict[str, Any],
        fayda_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Match user-provided data against Fayda records.
        """
        details = {}
        scores = []
        
        # Name matching
        if "full_name" in user_data:
            name_score = self._fuzzy_name_match(
                user_data["full_name"],
                fayda_data.get("full_name", "")
            )
            details["name_match"] = name_score > 0.85
            details["name_score"] = name_score
            scores.append(name_score)
        
        # Date of birth matching
        if "date_of_birth" in user_data:
            dob_match = user_data["date_of_birth"] == fayda_data.get("date_of_birth")
            details["dob_match"] = dob_match
            scores.append(1.0 if dob_match else 0.0)
        
        # Gender matching
        if "gender" in user_data:
            gender_match = user_data["gender"].lower() == fayda_data.get("gender", "").lower()
            details["gender_match"] = gender_match
            scores.append(1.0 if gender_match else 0.0)
        
        # Calculate overall score
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "is_match": overall_score > 0.80,
            "overall_score": overall_score,
            "details": details
        }
    
    def _fuzzy_name_match(self, name1: str, name2: str) -> float:
        """
        Perform fuzzy name matching.
        Uses simple comparison - in production, use proper fuzzy matching.
        """
        # Normalize names
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        
        if n1 == n2:
            return 1.0
        
        # Check if names contain each other
        if n1 in n2 or n2 in n1:
            return 0.9
        
        # Simple character overlap
        chars1 = set(n1.replace(" ", ""))
        chars2 = set(n2.replace(" ", ""))
        overlap = len(chars1 & chars2) / max(len(chars1), len(chars2))
        
        return overlap


class ConsentManager:
    """
    Manages user consent for Fayda data access.
    """
    
    def __init__(self):
        self.secret_key = os.getenv("CONSENT_SECRET_KEY", "dev_secret_key")
    
    def create_consent_token(
        self,
        user_id: str,
        fayda_id: str,
        scopes: list,
        expires_in: int = 3600
    ) -> str:
        """
        Create a consent token for Fayda data access.
        
        Args:
            user_id: User's internal ID
            fayda_id: User's Fayda ID
            scopes: Data access scopes (e.g., ["demographics", "biometrics"])
            expires_in: Token validity in seconds
            
        Returns:
            Signed consent token
        """
        import time
        import json
        import base64
        
        payload = {
            "user_id": user_id,
            "fayda_id": fayda_id,
            "scopes": scopes,
            "exp": int(time.time()) + expires_in,
            "iat": int(time.time())
        }
        
        # Create signature
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(
            self.secret_key.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        # Combine payload and signature
        token_data = {
            "payload": payload,
            "signature": signature
        }
        
        return base64.urlsafe_b64encode(json.dumps(token_data).encode()).decode()
    
    def verify_consent_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a consent token.
        """
        import time
        import json
        import base64
        
        try:
            token_data = json.loads(base64.urlsafe_b64decode(token))
            payload = token_data["payload"]
            signature = token_data["signature"]
            
            # Verify signature
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            expected_signature = hmac.new(
                self.secret_key.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            # Check expiration
            if payload["exp"] < time.time():
                return None
            
            return payload
            
        except Exception as e:
            logger.error(f"Error verifying consent token: {e}")
            return None
