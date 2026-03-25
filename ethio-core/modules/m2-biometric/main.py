"""
M2 Biometric Service - Face Matching & Liveness Detection
Ethiopian Banking Core Platform
"""

import asyncio
import base64
import hashlib
import io
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import aiohttp
import cv2
import numpy as np
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from PIL import Image
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.responses import Response

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/biometric_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
EVENT_STORE_URL = os.getenv("EVENT_STORE_URL", "http://event-store:8000")
IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://m1-identity:8001")
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.85"))
LIVENESS_THRESHOLD = float(os.getenv("LIVENESS_THRESHOLD", "0.90"))
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")

# Metrics
face_match_requests = Counter("biometric_face_match_total", "Total face match requests", ["status"])
liveness_checks = Counter("biometric_liveness_total", "Total liveness checks", ["result"])
face_match_latency = Histogram("biometric_face_match_seconds", "Face match latency")
enrollment_counter = Counter("biometric_enrollment_total", "Total enrollments", ["status"])

# Database setup
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20, max_overflow=30)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

security = HTTPBearer()


class BiometricType(str, Enum):
    FACE = "face"
    FINGERPRINT = "fingerprint"
    IRIS = "iris"


class LivenessResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class MatchResult(str, Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    ERROR = "error"


# Database Models
class BiometricTemplate(Base):
    __tablename__ = "biometric_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False, index=True)
    biometric_type = Column(String(20), nullable=False)
    template_hash = Column(String(128), nullable=False)
    template_data = Column(Text, nullable=False)  # Encrypted
    quality_score = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    enrollment_device = Column(String(100))
    enrollment_location = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)

    __table_args__ = (
        Index("idx_customer_biometric", "customer_id", "biometric_type"),
        Index("idx_template_hash", "template_hash"),
    )


class BiometricVerification(Base):
    __tablename__ = "biometric_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String(36), nullable=False)
    customer_id = Column(String(36), nullable=False)
    verification_type = Column(String(20), nullable=False)
    match_score = Column(Float)
    liveness_score = Column(Float)
    result = Column(String(20), nullable=False)
    device_info = Column(Text)
    ip_address = Column(String(45))
    location = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_verification_customer", "customer_id"),
        Index("idx_verification_date", "created_at"),
    )


class LivenessSession(Base):
    __tablename__ = "liveness_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False)
    session_token = Column(String(128), unique=True, nullable=False)
    challenge_type = Column(String(50), nullable=False)
    challenge_data = Column(Text)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    status = Column(String(20), default="pending")
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models
class EnrollmentRequest(BaseModel):
    customer_id: str
    biometric_type: BiometricType = BiometricType.FACE
    device_info: Optional[str] = None
    location: Optional[str] = None


class EnrollmentResponse(BaseModel):
    template_id: str
    customer_id: str
    biometric_type: str
    quality_score: float
    enrolled_at: datetime


class VerificationRequest(BaseModel):
    customer_id: str
    biometric_type: BiometricType = BiometricType.FACE
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    require_liveness: bool = True


class VerificationResponse(BaseModel):
    verification_id: str
    customer_id: str
    result: MatchResult
    match_score: float
    liveness_passed: Optional[bool] = None
    liveness_score: Optional[float] = None
    verified_at: datetime


class LivenessSessionRequest(BaseModel):
    customer_id: str
    challenge_type: str = "blink_detection"


class LivenessSessionResponse(BaseModel):
    session_id: str
    session_token: str
    challenge_type: str
    challenge_instructions: str
    expires_at: datetime


class LivenessVerifyRequest(BaseModel):
    session_token: str


class LivenessVerifyResponse(BaseModel):
    session_id: str
    result: LivenessResult
    score: float
    message: str


class FaceMatchRequest(BaseModel):
    customer_id: str
    threshold: Optional[float] = None


class FaceMatchResponse(BaseModel):
    match_id: str
    customer_id: str
    result: MatchResult
    confidence_score: float
    match_details: dict


# Face Processing Engine
class FaceProcessor:
    def __init__(self):
        self.face_cascade = None
        self._initialized = False

    async def initialize(self):
        """Initialize face detection models"""
        if self._initialized:
            return
        try:
            # Load Haar cascade for face detection
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            self._initialized = True
        except Exception as e:
            print(f"Failed to initialize face processor: {e}")

    async def extract_face_template(self, image_data: bytes) -> tuple[bytes, float]:
        """Extract face template from image"""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("Invalid image data")

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
            )

            if len(faces) == 0:
                raise ValueError("No face detected in image")

            if len(faces) > 1:
                raise ValueError("Multiple faces detected - please provide single face image")

            # Extract face region
            x, y, w, h = faces[0]
            face_region = gray[y : y + h, x : x + w]

            # Resize to standard size
            face_normalized = cv2.resize(face_region, (128, 128))

            # Calculate quality score based on image properties
            quality_score = self._calculate_quality_score(face_normalized)

            # Generate template (in production, use deep learning embeddings)
            template = face_normalized.tobytes()

            return template, quality_score

        except Exception as e:
            raise ValueError(f"Face extraction failed: {str(e)}")

    def _calculate_quality_score(self, face_image: np.ndarray) -> float:
        """Calculate face image quality score"""
        # Laplacian variance for blur detection
        laplacian_var = cv2.Laplacian(face_image, cv2.CV_64F).var()
        blur_score = min(laplacian_var / 500, 1.0)

        # Brightness score
        mean_brightness = np.mean(face_image)
        brightness_score = 1.0 - abs(mean_brightness - 127.5) / 127.5

        # Contrast score
        contrast = np.std(face_image)
        contrast_score = min(contrast / 64, 1.0)

        # Combined quality score
        quality = (blur_score * 0.4 + brightness_score * 0.3 + contrast_score * 0.3)
        return round(quality, 4)

    async def compare_templates(
        self, template1: bytes, template2: bytes
    ) -> tuple[float, dict]:
        """Compare two face templates"""
        try:
            # Convert templates back to arrays
            arr1 = np.frombuffer(template1, dtype=np.uint8).reshape(128, 128)
            arr2 = np.frombuffer(template2, dtype=np.uint8).reshape(128, 128)

            # Histogram comparison
            hist1 = cv2.calcHist([arr1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([arr2], [0], None, [256], [0, 256])

            # Normalize histograms
            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

            # Calculate correlation
            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

            # Structural similarity
            ssim_score = self._calculate_ssim(arr1, arr2)

            # Combined score
            match_score = (correlation * 0.4 + ssim_score * 0.6)

            details = {
                "histogram_correlation": round(correlation, 4),
                "structural_similarity": round(ssim_score, 4),
                "combined_score": round(match_score, 4),
            }

            return match_score, details

        except Exception as e:
            raise ValueError(f"Template comparison failed: {str(e)}")

    def _calculate_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calculate Structural Similarity Index"""
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2

        img1 = img1.astype(np.float64)
        img2 = img2.astype(np.float64)

        mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)

        mu1_sq = mu1**2
        mu2_sq = mu2**2
        mu1_mu2 = mu1 * mu2

        sigma1_sq = cv2.GaussianBlur(img1**2, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(img2**2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2

        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / (
            (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
        )

        return float(ssim_map.mean())


# Liveness Detection Engine
class LivenessDetector:
    CHALLENGE_TYPES = {
        "blink_detection": "Please blink your eyes naturally 2-3 times",
        "head_turn": "Please slowly turn your head left and right",
        "smile_detection": "Please smile naturally",
        "random_gesture": "Please follow the on-screen instructions",
    }

    async def create_challenge(self, challenge_type: str) -> dict:
        """Create a liveness challenge"""
        if challenge_type not in self.CHALLENGE_TYPES:
            challenge_type = "blink_detection"

        challenge_data = {
            "type": challenge_type,
            "instructions": self.CHALLENGE_TYPES[challenge_type],
            "parameters": self._get_challenge_parameters(challenge_type),
        }

        return challenge_data

    def _get_challenge_parameters(self, challenge_type: str) -> dict:
        """Get challenge-specific parameters"""
        params = {
            "blink_detection": {
                "min_blinks": 2,
                "max_blinks": 5,
                "detection_window_seconds": 5,
            },
            "head_turn": {
                "min_angle": 15,
                "max_angle": 45,
                "required_directions": ["left", "right"],
            },
            "smile_detection": {
                "min_smile_confidence": 0.7,
                "hold_duration_seconds": 2,
            },
            "random_gesture": {
                "gestures": ["blink", "smile", "head_left"],
                "sequence_length": 3,
            },
        }
        return params.get(challenge_type, {})

    async def verify_liveness(
        self, frames: list[bytes], challenge_type: str
    ) -> tuple[LivenessResult, float, str]:
        """Verify liveness from video frames"""
        try:
            if not frames or len(frames) < 5:
                return LivenessResult.FAILED, 0.0, "Insufficient frames for analysis"

            # Analyze frames for liveness indicators
            liveness_scores = []
            motion_detected = False
            face_consistent = True

            previous_face = None
            for frame_data in frames:
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    continue

                # Check for face presence and consistency
                face_score, face_location = self._detect_face_in_frame(frame)
                if face_score > 0:
                    liveness_scores.append(face_score)

                    if previous_face is not None:
                        # Check for motion between frames
                        motion = self._calculate_motion(previous_face, face_location)
                        if motion > 0.05:
                            motion_detected = True

                    previous_face = face_location

            if len(liveness_scores) < 3:
                return LivenessResult.FAILED, 0.0, "Face not consistently detected"

            # Calculate overall liveness score
            avg_score = np.mean(liveness_scores)
            score_variance = np.var(liveness_scores)

            # Liveness indicators
            has_natural_variation = 0.001 < score_variance < 0.1
            has_motion = motion_detected

            # Final score calculation
            final_score = avg_score
            if has_natural_variation:
                final_score += 0.1
            if has_motion:
                final_score += 0.1

            final_score = min(final_score, 1.0)

            if final_score >= LIVENESS_THRESHOLD:
                return LivenessResult.PASSED, final_score, "Liveness verification successful"
            elif final_score >= 0.7:
                return LivenessResult.INCONCLUSIVE, final_score, "Please try again with better lighting"
            else:
                return LivenessResult.FAILED, final_score, "Liveness verification failed"

        except Exception as e:
            return LivenessResult.FAILED, 0.0, f"Liveness verification error: {str(e)}"

    def _detect_face_in_frame(self, frame: np.ndarray) -> tuple[float, Optional[tuple]]:
        """Detect face in a single frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

        if len(faces) == 0:
            return 0.0, None

        # Return the largest face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face_region = gray[y : y + h, x : x + w]

        # Quality score
        quality = min(cv2.Laplacian(face_region, cv2.CV_64F).var() / 500, 1.0)

        return quality, (x, y, w, h)

    def _calculate_motion(self, prev_face: tuple, curr_face: tuple) -> float:
        """Calculate motion between two face detections"""
        if prev_face is None or curr_face is None:
            return 0.0

        px, py, pw, ph = prev_face
        cx, cy, cw, ch = curr_face

        # Calculate center point movement
        prev_center = (px + pw / 2, py + ph / 2)
        curr_center = (cx + cw / 2, cy + ch / 2)

        distance = np.sqrt(
            (curr_center[0] - prev_center[0]) ** 2
            + (curr_center[1] - prev_center[1]) ** 2
        )

        # Normalize by face size
        avg_size = (pw + ph + cw + ch) / 4
        normalized_motion = distance / avg_size if avg_size > 0 else 0

        return normalized_motion


# Event Publisher
class EventPublisher:
    def __init__(self, event_store_url: str):
        self.event_store_url = event_store_url

    async def publish(self, event_type: str, aggregate_id: str, data: dict):
        """Publish event to event store"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "aggregate_type": "biometric",
            "aggregate_id": aggregate_id,
            "data": data,
            "metadata": {
                "service": "m2-biometric",
                "version": "1.0.0",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.event_store_url}/events",
                    json=event,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status != 201:
                        print(f"Failed to publish event: {await response.text()}")
        except Exception as e:
            print(f"Event publish error: {e}")


# Initialize components
face_processor = FaceProcessor()
liveness_detector = LivenessDetector()
event_publisher = EventPublisher(EVENT_STORE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await face_processor.initialize()
    yield
    # Shutdown
    await engine.dispose()


# FastAPI Application
app = FastAPI(
    title="M2 Biometric Service",
    description="Face Matching & Liveness Detection for Ethiopian Banking",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db():
    async with async_session() as session:
        yield session


# Health & Metrics
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "m2-biometric", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")


# Enrollment Endpoints
@app.post("/api/v1/biometric/enroll", response_model=EnrollmentResponse)
async def enroll_biometric(
    request: EnrollmentRequest,
    image: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """Enroll biometric template for customer"""
    try:
        # Read image data
        image_data = await image.read()

        # Extract face template
        template_data, quality_score = await face_processor.extract_face_template(image_data)

        if quality_score < 0.5:
            enrollment_counter.labels(status="low_quality").inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image quality too low ({quality_score:.2f}). Please provide clearer image.",
            )

        # Generate template hash for deduplication
        template_hash = hashlib.sha256(template_data).hexdigest()

        # Check for existing enrollment
        result = await db.execute(
            text(
                "SELECT id FROM biometric_templates WHERE customer_id = :cid AND biometric_type = :btype AND is_active = true"
            ),
            {"cid": request.customer_id, "btype": request.biometric_type.value},
        )
        existing = result.fetchone()

        if existing:
            # Deactivate old template
            await db.execute(
                text("UPDATE biometric_templates SET is_active = false WHERE id = :id"),
                {"id": existing[0]},
            )

        # Create new template
        template = BiometricTemplate(
            customer_id=request.customer_id,
            biometric_type=request.biometric_type.value,
            template_hash=template_hash,
            template_data=base64.b64encode(template_data).decode(),
            quality_score=quality_score,
            enrollment_device=request.device_info,
            enrollment_location=request.location,
            expires_at=datetime.utcnow() + timedelta(days=365 * 2),
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        # Publish event
        background_tasks.add_task(
            event_publisher.publish,
            "BiometricEnrolled",
            request.customer_id,
            {
                "template_id": template.id,
                "biometric_type": request.biometric_type.value,
                "quality_score": quality_score,
            },
        )

        enrollment_counter.labels(status="success").inc()

        return EnrollmentResponse(
            template_id=template.id,
            customer_id=template.customer_id,
            biometric_type=template.biometric_type,
            quality_score=template.quality_score,
            enrolled_at=template.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        enrollment_counter.labels(status="error").inc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Verification Endpoints
@app.post("/api/v1/biometric/verify", response_model=VerificationResponse)
async def verify_biometric(
    request: VerificationRequest,
    image: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """Verify biometric against enrolled template"""
    with face_match_latency.time():
        try:
            # Get enrolled template
            result = await db.execute(
                text(
                    """SELECT id, template_data, quality_score FROM biometric_templates 
                       WHERE customer_id = :cid AND biometric_type = :btype AND is_active = true
                       ORDER BY created_at DESC LIMIT 1"""
                ),
                {"cid": request.customer_id, "btype": request.biometric_type.value},
            )
            template_row = result.fetchone()

            if not template_row:
                face_match_requests.labels(status="not_enrolled").inc()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No biometric template enrolled for this customer",
                )

            template_id, stored_template_b64, stored_quality = template_row
            stored_template = base64.b64decode(stored_template_b64)

            # Extract template from verification image
            image_data = await image.read()
            verify_template, verify_quality = await face_processor.extract_face_template(image_data)

            # Compare templates
            match_score, match_details = await face_processor.compare_templates(
                stored_template, verify_template
            )

            # Determine result
            result_status = MatchResult.MATCH if match_score >= FACE_MATCH_THRESHOLD else MatchResult.NO_MATCH

            # Create verification record
            verification = BiometricVerification(
                template_id=template_id,
                customer_id=request.customer_id,
                verification_type=request.biometric_type.value,
                match_score=match_score,
                result=result_status.value,
                device_info=request.device_info,
                ip_address=request.ip_address,
            )

            db.add(verification)
            await db.commit()
            await db.refresh(verification)

            # Publish event
            background_tasks.add_task(
                event_publisher.publish,
                "BiometricVerified",
                request.customer_id,
                {
                    "verification_id": verification.id,
                    "result": result_status.value,
                    "match_score": match_score,
                },
            )

            face_match_requests.labels(status=result_status.value).inc()

            return VerificationResponse(
                verification_id=verification.id,
                customer_id=request.customer_id,
                result=result_status,
                match_score=match_score,
                verified_at=verification.created_at,
            )

        except HTTPException:
            raise
        except Exception as e:
            face_match_requests.labels(status="error").inc()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Liveness Endpoints
@app.post("/api/v1/biometric/liveness/session", response_model=LivenessSessionResponse)
async def create_liveness_session(
    request: LivenessSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new liveness verification session"""
    challenge = await liveness_detector.create_challenge(request.challenge_type)

    session_token = hashlib.sha256(
        f"{request.customer_id}{datetime.utcnow().isoformat()}{uuid.uuid4()}".encode()
    ).hexdigest()

    session = LivenessSession(
        customer_id=request.customer_id,
        session_token=session_token,
        challenge_type=challenge["type"],
        challenge_data=str(challenge["parameters"]),
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return LivenessSessionResponse(
        session_id=session.id,
        session_token=session_token,
        challenge_type=challenge["type"],
        challenge_instructions=challenge["instructions"],
        expires_at=session.expires_at,
    )


@app.post("/api/v1/biometric/liveness/verify", response_model=LivenessVerifyResponse)
async def verify_liveness(
    request: LivenessVerifyRequest,
    frames: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Verify liveness using video frames"""
    # Get session
    result = await db.execute(
        text(
            """SELECT id, customer_id, challenge_type, attempts, max_attempts, status, expires_at 
               FROM liveness_sessions WHERE session_token = :token"""
        ),
        {"token": request.session_token},
    )
    session_row = result.fetchone()

    if not session_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid session token")

    session_id, customer_id, challenge_type, attempts, max_attempts, sess_status, expires_at = session_row

    if sess_status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session already completed")

    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session expired")

    if attempts >= max_attempts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum attempts exceeded")

    # Update attempt count
    await db.execute(
        text("UPDATE liveness_sessions SET attempts = attempts + 1 WHERE id = :id"),
        {"id": session_id},
    )

    # Read frames
    frame_data = []
    for frame in frames:
        data = await frame.read()
        frame_data.append(data)

    # Verify liveness
    liveness_result, score, message = await liveness_detector.verify_liveness(
        frame_data, challenge_type
    )

    # Update session status if passed
    if liveness_result == LivenessResult.PASSED:
        await db.execute(
            text("UPDATE liveness_sessions SET status = 'completed', completed_at = :now WHERE id = :id"),
            {"id": session_id, "now": datetime.utcnow()},
        )

    await db.commit()

    liveness_checks.labels(result=liveness_result.value).inc()

    return LivenessVerifyResponse(
        session_id=session_id,
        result=liveness_result,
        score=score,
        message=message,
    )


# Face Match Endpoint
@app.post("/api/v1/biometric/match", response_model=FaceMatchResponse)
async def face_match(
    request: FaceMatchRequest,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Perform 1:1 face matching"""
    with face_match_latency.time():
        try:
            # Get stored template
            result = await db.execute(
                text(
                    """SELECT template_data FROM biometric_templates 
                       WHERE customer_id = :cid AND biometric_type = 'face' AND is_active = true"""
                ),
                {"cid": request.customer_id},
            )
            row = result.fetchone()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No face template enrolled",
                )

            stored_template = base64.b64decode(row[0])

            # Process uploaded image
            image_data = await image.read()
            probe_template, quality = await face_processor.extract_face_template(image_data)

            # Compare
            score, details = await face_processor.compare_templates(stored_template, probe_template)

            threshold = request.threshold or FACE_MATCH_THRESHOLD
            match_result = MatchResult.MATCH if score >= threshold else MatchResult.NO_MATCH

            return FaceMatchResponse(
                match_id=str(uuid.uuid4()),
                customer_id=request.customer_id,
                result=match_result,
                confidence_score=score,
                match_details={
                    **details,
                    "probe_quality": quality,
                    "threshold_used": threshold,
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
