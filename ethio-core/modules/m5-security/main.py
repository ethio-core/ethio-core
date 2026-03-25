"""
M5 Security Service - Fraud Detection, AML & Risk Scoring
Ethiopian Banking Core Platform
"""

import asyncio
import hashlib
import json
import os
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

import aiohttp
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.responses import Response

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/security_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/4")
EVENT_STORE_URL = os.getenv("EVENT_STORE_URL", "http://event-store:8000")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")

# Risk thresholds
HIGH_RISK_THRESHOLD = float(os.getenv("HIGH_RISK_THRESHOLD", "0.7"))
MEDIUM_RISK_THRESHOLD = float(os.getenv("MEDIUM_RISK_THRESHOLD", "0.4"))
FRAUD_BLOCK_THRESHOLD = float(os.getenv("FRAUD_BLOCK_THRESHOLD", "0.85"))

# AML thresholds (in ETB)
AML_SINGLE_THRESHOLD = float(os.getenv("AML_SINGLE_THRESHOLD", "100000"))
AML_DAILY_THRESHOLD = float(os.getenv("AML_DAILY_THRESHOLD", "500000"))
AML_MONTHLY_THRESHOLD = float(os.getenv("AML_MONTHLY_THRESHOLD", "2000000"))

# Metrics
fraud_checks = Counter("security_fraud_checks_total", "Total fraud checks", ["result"])
aml_alerts = Counter("security_aml_alerts_total", "AML alerts generated", ["severity"])
risk_scores = Histogram("security_risk_score", "Risk score distribution", buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
blocked_transactions = Counter("security_blocked_transactions_total", "Blocked transactions", ["reason"])
active_investigations = Gauge("security_active_investigations", "Active fraud investigations")

# Database setup
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20, max_overflow=30)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

security_bearer = HTTPBearer()


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    FRAUD = "fraud"
    AML = "aml"
    SUSPICIOUS = "suspicious"
    VELOCITY = "velocity"
    GEOGRAPHIC = "geographic"
    DEVICE = "device"
    BEHAVIORAL = "behavioral"


class AlertStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class TransactionDecision(str, Enum):
    APPROVE = "approve"
    BLOCK = "block"
    REVIEW = "review"
    CHALLENGE = "challenge"


# Database Models
class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False, unique=True)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(20), default=RiskLevel.LOW.value)
    pep_status = Column(Boolean, default=False)  # Politically Exposed Person
    sanctions_match = Column(Boolean, default=False)
    adverse_media = Column(Boolean, default=False)
    kyc_risk_score = Column(Float, default=0.0)
    transaction_risk_score = Column(Float, default=0.0)
    behavioral_risk_score = Column(Float, default=0.0)
    last_review_date = Column(DateTime)
    next_review_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_risk_customer", "customer_id"),
        Index("idx_risk_level", "risk_level"),
    )


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False, index=True)
    transaction_id = Column(String(36), index=True)
    alert_type = Column(String(30), nullable=False)
    severity = Column(String(20), nullable=False)
    risk_score = Column(Float, nullable=False)
    description = Column(Text, nullable=False)
    indicators = Column(Text)  # JSON
    status = Column(String(20), default=AlertStatus.OPEN.value)
    assigned_to = Column(String(36))
    resolution = Column(Text)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_alert_status", "status"),
        Index("idx_alert_date", "created_at"),
    )


class AMLReport(Base):
    __tablename__ = "aml_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False, index=True)
    report_type = Column(String(30), nullable=False)  # STR, CTR, SAR
    threshold_type = Column(String(30))
    amount_involved = Column(Float)
    currency = Column(String(3), default="ETB")
    description = Column(Text)
    transactions_involved = Column(Text)  # JSON list of transaction IDs
    risk_indicators = Column(Text)  # JSON
    status = Column(String(20), default="pending")
    filed_to_fic = Column(Boolean, default=False)  # Financial Intelligence Center
    fic_reference = Column(String(50))
    filed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class TransactionRisk(Base):
    __tablename__ = "transaction_risks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String(36), nullable=False, unique=True)
    customer_id = Column(String(36), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_factors = Column(Text)  # JSON
    decision = Column(String(20), nullable=False)
    rules_triggered = Column(Text)  # JSON list
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_txn_risk_date", "created_at"),)


class SecurityRule(Base):
    __tablename__ = "security_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    rule_type = Column(String(30), nullable=False)
    conditions = Column(Text, nullable=False)  # JSON
    action = Column(String(20), nullable=False)
    risk_weight = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeviceFingerprint(Base):
    __tablename__ = "device_fingerprints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False, index=True)
    device_id = Column(String(100), nullable=False)
    device_hash = Column(String(128), nullable=False)
    device_type = Column(String(30))
    os_name = Column(String(50))
    os_version = Column(String(20))
    browser = Column(String(50))
    ip_address = Column(String(45))
    location = Column(String(200))
    is_trusted = Column(Boolean, default=False)
    last_used_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_device_customer", "customer_id"),
        Index("idx_device_hash", "device_hash"),
    )


class CustomerBehavior(Base):
    __tablename__ = "customer_behaviors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False, unique=True)
    avg_transaction_amount = Column(Float, default=0)
    max_transaction_amount = Column(Float, default=0)
    avg_daily_transactions = Column(Float, default=0)
    typical_transaction_hours = Column(Text)  # JSON array
    typical_locations = Column(Text)  # JSON array
    typical_merchants = Column(Text)  # JSON array
    international_activity = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow)


# Pydantic Models
class TransactionRiskRequest(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    currency: str = "ETB"
    transaction_type: str
    source_account: Optional[str] = None
    destination_account: Optional[str] = None
    destination_bank: Optional[str] = None
    channel: str = "mobile"
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None
    is_international: bool = False
    timestamp: Optional[datetime] = None


class TransactionRiskResponse(BaseModel):
    transaction_id: str
    risk_score: float
    risk_level: RiskLevel
    decision: TransactionDecision
    rules_triggered: list[str]
    requires_review: bool
    challenge_required: bool
    processing_time_ms: int


class CustomerRiskRequest(BaseModel):
    customer_id: str
    include_history: bool = False


class CustomerRiskResponse(BaseModel):
    customer_id: str
    risk_score: float
    risk_level: RiskLevel
    pep_status: bool
    sanctions_match: bool
    kyc_risk_score: float
    transaction_risk_score: float
    behavioral_risk_score: float
    active_alerts: int
    last_review_date: Optional[datetime] = None


class FraudAlertRequest(BaseModel):
    customer_id: str
    transaction_id: Optional[str] = None
    alert_type: AlertType
    severity: RiskLevel
    description: str
    indicators: Optional[dict] = None


class FraudAlertResponse(BaseModel):
    alert_id: str
    customer_id: str
    alert_type: str
    severity: str
    status: str
    description: str
    created_at: datetime


class DeviceFingerprintRequest(BaseModel):
    customer_id: str
    device_id: str
    device_type: Optional[str] = None
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    browser: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None


class AMLCheckRequest(BaseModel):
    customer_id: str
    transaction_id: str
    amount: float
    currency: str = "ETB"
    transaction_type: str


class AMLCheckResponse(BaseModel):
    requires_report: bool
    report_type: Optional[str] = None
    risk_indicators: list[str]
    threshold_exceeded: Optional[str] = None


# Risk Engine
class RiskEngine:
    """Core risk scoring engine"""

    # Rule weights
    RULE_WEIGHTS = {
        "high_amount": 0.25,
        "unusual_time": 0.15,
        "new_device": 0.20,
        "unusual_location": 0.20,
        "velocity_breach": 0.30,
        "high_risk_merchant": 0.15,
        "international": 0.10,
        "pep_involved": 0.25,
        "behavioral_anomaly": 0.25,
    }

    async def calculate_transaction_risk(
        self,
        db: AsyncSession,
        request: TransactionRiskRequest,
        customer_behavior: Optional[CustomerBehavior] = None,
    ) -> tuple[float, list[str], TransactionDecision]:
        """Calculate comprehensive transaction risk score"""
        import time

        start_time = time.time()

        risk_factors = []
        risk_score = 0.0

        # 1. Amount-based risk
        amount_risk, amount_factors = await self._check_amount_risk(
            request.amount, request.customer_id, customer_behavior
        )
        risk_score += amount_risk
        risk_factors.extend(amount_factors)

        # 2. Velocity checks
        velocity_risk, velocity_factors = await self._check_velocity(
            db, request.customer_id, request.amount
        )
        risk_score += velocity_risk
        risk_factors.extend(velocity_factors)

        # 3. Device risk
        if request.device_id:
            device_risk, device_factors = await self._check_device_risk(
                db, request.customer_id, request.device_id
            )
            risk_score += device_risk
            risk_factors.extend(device_factors)

        # 4. Geographic risk
        if request.location:
            geo_risk, geo_factors = await self._check_geographic_risk(
                db, request.customer_id, request.location, request.is_international
            )
            risk_score += geo_risk
            risk_factors.extend(geo_factors)

        # 5. Time-based risk
        time_risk, time_factors = self._check_time_risk(
            request.timestamp or datetime.utcnow(), customer_behavior
        )
        risk_score += time_risk
        risk_factors.extend(time_factors)

        # 6. Merchant risk
        if request.merchant_category:
            merchant_risk, merchant_factors = self._check_merchant_risk(
                request.merchant_category, request.merchant_name
            )
            risk_score += merchant_risk
            risk_factors.extend(merchant_factors)

        # 7. Customer profile risk
        profile_risk, profile_factors = await self._check_customer_profile(
            db, request.customer_id
        )
        risk_score += profile_risk
        risk_factors.extend(profile_factors)

        # Normalize score to 0-1
        risk_score = min(risk_score, 1.0)

        # Determine decision
        decision = self._determine_decision(risk_score)

        processing_time = int((time.time() - start_time) * 1000)

        return risk_score, risk_factors, decision

    async def _check_amount_risk(
        self,
        amount: float,
        customer_id: str,
        behavior: Optional[CustomerBehavior],
    ) -> tuple[float, list[str]]:
        """Check amount-related risks"""
        factors = []
        risk = 0.0

        # Check against AML thresholds
        if amount >= AML_SINGLE_THRESHOLD:
            risk += 0.3
            factors.append(f"amount_exceeds_aml_threshold_{AML_SINGLE_THRESHOLD}")

        # Check against customer's typical behavior
        if behavior:
            if behavior.max_transaction_amount > 0:
                if amount > behavior.max_transaction_amount * 2:
                    risk += 0.25
                    factors.append("amount_exceeds_2x_historical_max")
                elif amount > behavior.max_transaction_amount * 1.5:
                    risk += 0.15
                    factors.append("amount_exceeds_1.5x_historical_max")

            if behavior.avg_transaction_amount > 0:
                if amount > behavior.avg_transaction_amount * 5:
                    risk += 0.20
                    factors.append("amount_exceeds_5x_average")

        return risk, factors

    async def _check_velocity(
        self, db: AsyncSession, customer_id: str, current_amount: float
    ) -> tuple[float, list[str]]:
        """Check transaction velocity"""
        factors = []
        risk = 0.0

        # Check transactions in last hour
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        result = await db.execute(
            text(
                """SELECT COUNT(*), COALESCE(SUM(amount), 0) 
                   FROM transaction_risks 
                   WHERE customer_id = :cid AND created_at >= :since"""
            ),
            {"cid": customer_id, "since": hour_ago},
        )
        row = result.fetchone()
        hourly_count, hourly_amount = row[0], float(row[1])

        if hourly_count >= 10:
            risk += 0.3
            factors.append("high_hourly_transaction_count")

        if hourly_amount + current_amount > 100000:
            risk += 0.25
            factors.append("high_hourly_amount")

        # Check transactions in last 24 hours
        day_ago = datetime.utcnow() - timedelta(hours=24)
        result = await db.execute(
            text(
                """SELECT COUNT(*), COALESCE(SUM(amount), 0) 
                   FROM transaction_risks 
                   WHERE customer_id = :cid AND created_at >= :since"""
            ),
            {"cid": customer_id, "since": day_ago},
        )
        row = result.fetchone()
        daily_count, daily_amount = row[0], float(row[1])

        if daily_amount + current_amount > AML_DAILY_THRESHOLD:
            risk += 0.35
            factors.append("daily_amount_exceeds_aml_threshold")

        return risk, factors

    async def _check_device_risk(
        self, db: AsyncSession, customer_id: str, device_id: str
    ) -> tuple[float, list[str]]:
        """Check device-related risks"""
        factors = []
        risk = 0.0

        device_hash = hashlib.sha256(device_id.encode()).hexdigest()

        result = await db.execute(
            text(
                """SELECT * FROM device_fingerprints 
                   WHERE customer_id = :cid AND device_hash = :hash"""
            ),
            {"cid": customer_id, "hash": device_hash},
        )
        device = result.fetchone()

        if not device:
            risk += 0.2
            factors.append("new_device")
        elif not device.is_trusted:
            risk += 0.1
            factors.append("untrusted_device")

        # Check how many devices this customer has
        result = await db.execute(
            text("SELECT COUNT(*) FROM device_fingerprints WHERE customer_id = :cid"),
            {"cid": customer_id},
        )
        device_count = result.scalar()

        if device_count > 5:
            risk += 0.15
            factors.append("multiple_devices")

        return risk, factors

    async def _check_geographic_risk(
        self,
        db: AsyncSession,
        customer_id: str,
        location: str,
        is_international: bool,
    ) -> tuple[float, list[str]]:
        """Check geographic risks"""
        factors = []
        risk = 0.0

        if is_international:
            risk += 0.15
            factors.append("international_transaction")

        # Check against typical locations
        result = await db.execute(
            text("SELECT typical_locations FROM customer_behaviors WHERE customer_id = :cid"),
            {"cid": customer_id},
        )
        row = result.fetchone()

        if row and row[0]:
            typical_locations = json.loads(row[0]) if row[0] else []
            if location and location not in typical_locations:
                risk += 0.2
                factors.append("unusual_location")

        # High-risk countries (simplified list)
        high_risk_indicators = ["nigeria", "russia", "china", "iran", "north korea"]
        if location and any(c in location.lower() for c in high_risk_indicators):
            risk += 0.3
            factors.append("high_risk_country")

        return risk, factors

    def _check_time_risk(
        self, timestamp: datetime, behavior: Optional[CustomerBehavior]
    ) -> tuple[float, list[str]]:
        """Check time-based risks"""
        factors = []
        risk = 0.0

        hour = timestamp.hour

        # Late night transactions (midnight to 5am)
        if 0 <= hour < 5:
            risk += 0.15
            factors.append("late_night_transaction")

        # Check against typical hours
        if behavior and behavior.typical_transaction_hours:
            typical_hours = json.loads(behavior.typical_transaction_hours)
            if hour not in typical_hours:
                risk += 0.1
                factors.append("unusual_transaction_hour")

        return risk, factors

    def _check_merchant_risk(
        self, merchant_category: str, merchant_name: Optional[str]
    ) -> tuple[float, list[str]]:
        """Check merchant-related risks"""
        factors = []
        risk = 0.0

        # High-risk merchant categories
        high_risk_mcc = ["7995", "7801", "7802", "5967", "5966", "4829"]  # Gambling, crypto, etc.
        if merchant_category in high_risk_mcc:
            risk += 0.25
            factors.append("high_risk_merchant_category")

        # Medium risk categories
        medium_risk_mcc = ["5912", "5944", "5999"]  # Pawn shops, etc.
        if merchant_category in medium_risk_mcc:
            risk += 0.1
            factors.append("medium_risk_merchant_category")

        return risk, factors

    async def _check_customer_profile(
        self, db: AsyncSession, customer_id: str
    ) -> tuple[float, list[str]]:
        """Check customer profile risks"""
        factors = []
        risk = 0.0

        result = await db.execute(
            text("SELECT * FROM risk_profiles WHERE customer_id = :cid"),
            {"cid": customer_id},
        )
        profile = result.fetchone()

        if profile:
            if profile.pep_status:
                risk += 0.25
                factors.append("pep_customer")

            if profile.sanctions_match:
                risk += 0.5
                factors.append("sanctions_match")

            if profile.adverse_media:
                risk += 0.15
                factors.append("adverse_media")

            # Add existing risk score
            risk += profile.risk_score * 0.2

        return risk, factors

    def _determine_decision(self, risk_score: float) -> TransactionDecision:
        """Determine transaction decision based on risk score"""
        if risk_score >= FRAUD_BLOCK_THRESHOLD:
            return TransactionDecision.BLOCK
        elif risk_score >= HIGH_RISK_THRESHOLD:
            return TransactionDecision.CHALLENGE
        elif risk_score >= MEDIUM_RISK_THRESHOLD:
            return TransactionDecision.REVIEW
        else:
            return TransactionDecision.APPROVE


# AML Engine
class AMLEngine:
    """Anti-Money Laundering detection engine"""

    async def check_transaction(
        self, db: AsyncSession, request: AMLCheckRequest
    ) -> tuple[bool, Optional[str], list[str]]:
        """Check transaction for AML concerns"""
        indicators = []
        requires_report = False
        report_type = None

        # Check single transaction threshold (CTR - Currency Transaction Report)
        if request.amount >= AML_SINGLE_THRESHOLD:
            requires_report = True
            report_type = "CTR"
            indicators.append(f"single_transaction_exceeds_{AML_SINGLE_THRESHOLD}_ETB")

        # Check for structuring (multiple transactions just below threshold)
        structuring = await self._check_structuring(db, request.customer_id, request.amount)
        if structuring:
            requires_report = True
            report_type = "SAR"  # Suspicious Activity Report
            indicators.append("potential_structuring_detected")

        # Check daily aggregate
        daily_total = await self._get_daily_total(db, request.customer_id)
        if daily_total + request.amount >= AML_DAILY_THRESHOLD:
            indicators.append("daily_aggregate_threshold_exceeded")
            if not requires_report:
                requires_report = True
                report_type = "CTR"

        # Check monthly aggregate
        monthly_total = await self._get_monthly_total(db, request.customer_id)
        if monthly_total + request.amount >= AML_MONTHLY_THRESHOLD:
            indicators.append("monthly_aggregate_threshold_exceeded")

        # Check for round amounts (potential layering)
        if request.amount >= 10000 and request.amount % 10000 == 0:
            indicators.append("round_amount_indicator")

        return requires_report, report_type, indicators

    async def _check_structuring(
        self, db: AsyncSession, customer_id: str, current_amount: float
    ) -> bool:
        """Check for structuring patterns"""
        # Look for multiple transactions just below threshold
        threshold_window = AML_SINGLE_THRESHOLD * 0.9
        day_ago = datetime.utcnow() - timedelta(hours=24)

        result = await db.execute(
            text(
                """SELECT COUNT(*) FROM transaction_risks 
                   WHERE customer_id = :cid 
                   AND created_at >= :since
                   AND risk_score > 0"""
            ),
            {"cid": customer_id, "since": day_ago},
        )
        count = result.scalar()

        # If multiple transactions and current is also below threshold
        if count >= 3 and threshold_window <= current_amount < AML_SINGLE_THRESHOLD:
            return True

        return False

    async def _get_daily_total(self, db: AsyncSession, customer_id: str) -> float:
        """Get daily transaction total"""
        today = datetime.utcnow().date()
        result = await db.execute(
            text(
                """SELECT COALESCE(SUM(t.amount), 0) 
                   FROM transaction_risks t
                   WHERE t.customer_id = :cid 
                   AND DATE(t.created_at) = :date"""
            ),
            {"cid": customer_id, "date": today},
        )
        return float(result.scalar() or 0)

    async def _get_monthly_total(self, db: AsyncSession, customer_id: str) -> float:
        """Get monthly transaction total"""
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        result = await db.execute(
            text(
                """SELECT COALESCE(SUM(t.amount), 0) 
                   FROM transaction_risks t
                   WHERE t.customer_id = :cid 
                   AND t.created_at >= :start"""
            ),
            {"cid": customer_id, "start": month_start},
        )
        return float(result.scalar() or 0)


# Event Publisher
class EventPublisher:
    def __init__(self, event_store_url: str):
        self.event_store_url = event_store_url

    async def publish(self, event_type: str, aggregate_id: str, data: dict):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "aggregate_type": "security",
            "aggregate_id": aggregate_id,
            "data": data,
            "metadata": {"service": "m5-security", "version": "1.0.0"},
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
risk_engine = RiskEngine()
aml_engine = AMLEngine()
event_publisher = EventPublisher(EVENT_STORE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# FastAPI Application
app = FastAPI(
    title="M5 Security Service",
    description="Fraud Detection, AML & Risk Scoring for Ethiopian Banking",
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
    return {"status": "healthy", "service": "m5-security", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")


# Transaction Risk Assessment
@app.post("/api/v1/risk/transaction", response_model=TransactionRiskResponse)
async def assess_transaction_risk(
    request: TransactionRiskRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Assess risk for a transaction"""
    import time

    start_time = time.time()

    # Get customer behavior
    result = await db.execute(
        text("SELECT * FROM customer_behaviors WHERE customer_id = :cid"),
        {"cid": request.customer_id},
    )
    behavior = result.fetchone()

    # Calculate risk
    risk_score, risk_factors, decision = await risk_engine.calculate_transaction_risk(
        db, request, behavior
    )

    processing_time = int((time.time() - start_time) * 1000)

    # Determine risk level
    if risk_score >= HIGH_RISK_THRESHOLD:
        risk_level = RiskLevel.HIGH
    elif risk_score >= MEDIUM_RISK_THRESHOLD:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    # Store risk assessment
    txn_risk = TransactionRisk(
        transaction_id=request.transaction_id,
        customer_id=request.customer_id,
        risk_score=risk_score,
        risk_factors=json.dumps(risk_factors),
        decision=decision.value,
        rules_triggered=json.dumps(risk_factors),
        processing_time_ms=processing_time,
    )
    db.add(txn_risk)
    await db.commit()

    # Record metrics
    risk_scores.observe(risk_score)
    fraud_checks.labels(result=decision.value).inc()

    if decision == TransactionDecision.BLOCK:
        blocked_transactions.labels(reason="high_risk").inc()

        # Create alert for blocked transactions
        background_tasks.add_task(
            create_fraud_alert_task,
            request.customer_id,
            request.transaction_id,
            risk_score,
            risk_factors,
        )

    return TransactionRiskResponse(
        transaction_id=request.transaction_id,
        risk_score=risk_score,
        risk_level=risk_level,
        decision=decision,
        rules_triggered=risk_factors,
        requires_review=decision == TransactionDecision.REVIEW,
        challenge_required=decision == TransactionDecision.CHALLENGE,
        processing_time_ms=processing_time,
    )


async def create_fraud_alert_task(
    customer_id: str,
    transaction_id: str,
    risk_score: float,
    risk_factors: list[str],
):
    """Background task to create fraud alert"""
    async with async_session() as db:
        alert = FraudAlert(
            customer_id=customer_id,
            transaction_id=transaction_id,
            alert_type=AlertType.FRAUD.value,
            severity=RiskLevel.HIGH.value if risk_score >= HIGH_RISK_THRESHOLD else RiskLevel.MEDIUM.value,
            risk_score=risk_score,
            description=f"High-risk transaction detected with score {risk_score:.2f}",
            indicators=json.dumps(risk_factors),
        )
        db.add(alert)
        await db.commit()

        aml_alerts.labels(severity=alert.severity).inc()
        active_investigations.inc()


# Customer Risk Profile
@app.get("/api/v1/risk/customer/{customer_id}", response_model=CustomerRiskResponse)
async def get_customer_risk(customer_id: str, db: AsyncSession = Depends(get_db)):
    """Get customer risk profile"""
    result = await db.execute(
        text("SELECT * FROM risk_profiles WHERE customer_id = :cid"),
        {"cid": customer_id},
    )
    profile = result.fetchone()

    if not profile:
        # Create default profile
        new_profile = RiskProfile(customer_id=customer_id)
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        profile = new_profile

    # Count active alerts
    alert_result = await db.execute(
        text(
            """SELECT COUNT(*) FROM fraud_alerts 
               WHERE customer_id = :cid AND status IN ('open', 'investigating')"""
        ),
        {"cid": customer_id},
    )
    active_alerts = alert_result.scalar()

    risk_level = RiskLevel.LOW
    if profile.risk_score >= HIGH_RISK_THRESHOLD:
        risk_level = RiskLevel.HIGH
    elif profile.risk_score >= MEDIUM_RISK_THRESHOLD:
        risk_level = RiskLevel.MEDIUM

    return CustomerRiskResponse(
        customer_id=customer_id,
        risk_score=profile.risk_score,
        risk_level=risk_level,
        pep_status=profile.pep_status,
        sanctions_match=profile.sanctions_match,
        kyc_risk_score=profile.kyc_risk_score,
        transaction_risk_score=profile.transaction_risk_score,
        behavioral_risk_score=profile.behavioral_risk_score,
        active_alerts=active_alerts,
        last_review_date=profile.last_review_date,
    )


@app.put("/api/v1/risk/customer/{customer_id}")
async def update_customer_risk(
    customer_id: str,
    risk_score: Optional[float] = None,
    pep_status: Optional[bool] = None,
    sanctions_match: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """Update customer risk profile"""
    result = await db.execute(
        text("SELECT * FROM risk_profiles WHERE customer_id = :cid"),
        {"cid": customer_id},
    )
    profile = result.fetchone()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk profile not found")

    updates = []
    params = {"cid": customer_id}

    if risk_score is not None:
        updates.append("risk_score = :score")
        params["score"] = risk_score

    if pep_status is not None:
        updates.append("pep_status = :pep")
        params["pep"] = pep_status

    if sanctions_match is not None:
        updates.append("sanctions_match = :sanctions")
        params["sanctions"] = sanctions_match

    if updates:
        await db.execute(
            text(f"UPDATE risk_profiles SET {', '.join(updates)} WHERE customer_id = :cid"),
            params,
        )
        await db.commit()

    return {"message": "Risk profile updated"}


# AML Checks
@app.post("/api/v1/aml/check", response_model=AMLCheckResponse)
async def check_aml(
    request: AMLCheckRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Check transaction for AML compliance"""
    requires_report, report_type, indicators = await aml_engine.check_transaction(db, request)

    if requires_report:
        # Create AML report
        background_tasks.add_task(
            create_aml_report_task,
            request.customer_id,
            request.transaction_id,
            request.amount,
            report_type,
            indicators,
        )

    return AMLCheckResponse(
        requires_report=requires_report,
        report_type=report_type,
        risk_indicators=indicators,
        threshold_exceeded=report_type if requires_report else None,
    )


async def create_aml_report_task(
    customer_id: str,
    transaction_id: str,
    amount: float,
    report_type: str,
    indicators: list[str],
):
    """Background task to create AML report"""
    async with async_session() as db:
        report = AMLReport(
            customer_id=customer_id,
            report_type=report_type,
            threshold_type="single" if report_type == "CTR" else "aggregate",
            amount_involved=amount,
            description=f"AML {report_type} for transaction {transaction_id}",
            transactions_involved=json.dumps([transaction_id]),
            risk_indicators=json.dumps(indicators),
        )
        db.add(report)
        await db.commit()

        aml_alerts.labels(severity=report_type).inc()


# Fraud Alerts
@app.post("/api/v1/alerts", response_model=FraudAlertResponse)
async def create_alert(
    request: FraudAlertRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a fraud alert"""
    alert = FraudAlert(
        customer_id=request.customer_id,
        transaction_id=request.transaction_id,
        alert_type=request.alert_type.value,
        severity=request.severity.value,
        risk_score=0.0,
        description=request.description,
        indicators=json.dumps(request.indicators) if request.indicators else None,
    )

    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    aml_alerts.labels(severity=request.severity.value).inc()
    active_investigations.inc()

    background_tasks.add_task(
        event_publisher.publish,
        "FraudAlertCreated",
        alert.id,
        {"customer_id": request.customer_id, "type": request.alert_type.value},
    )

    return FraudAlertResponse(
        alert_id=alert.id,
        customer_id=alert.customer_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        status=alert.status,
        description=alert.description,
        created_at=alert.created_at,
    )


@app.get("/api/v1/alerts")
async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    customer_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List fraud alerts"""
    query = "SELECT * FROM fraud_alerts WHERE 1=1"
    params = {}

    if status:
        query += " AND status = :status"
        params["status"] = status

    if severity:
        query += " AND severity = :severity"
        params["severity"] = severity

    if customer_id:
        query += " AND customer_id = :cid"
        params["cid"] = customer_id

    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size

    result = await db.execute(text(query), params)
    alerts = result.fetchall()

    return {
        "alerts": [
            {
                "alert_id": a.id,
                "customer_id": a.customer_id,
                "transaction_id": a.transaction_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "status": a.status,
                "description": a.description,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "page": page,
        "page_size": page_size,
    }


@app.put("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution: str,
    is_false_positive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Resolve a fraud alert"""
    result = await db.execute(
        text("SELECT * FROM fraud_alerts WHERE id = :id"), {"id": alert_id}
    )
    alert = result.fetchone()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    new_status = AlertStatus.FALSE_POSITIVE.value if is_false_positive else AlertStatus.RESOLVED.value

    await db.execute(
        text(
            """UPDATE fraud_alerts 
               SET status = :status, resolution = :resolution, resolved_at = :now 
               WHERE id = :id"""
        ),
        {"status": new_status, "resolution": resolution, "now": datetime.utcnow(), "id": alert_id},
    )
    await db.commit()

    active_investigations.dec()

    return {"message": "Alert resolved", "status": new_status}


# Device Management
@app.post("/api/v1/devices/register")
async def register_device(request: DeviceFingerprintRequest, db: AsyncSession = Depends(get_db)):
    """Register a device for a customer"""
    device_hash = hashlib.sha256(request.device_id.encode()).hexdigest()

    # Check if device exists
    result = await db.execute(
        text(
            """SELECT * FROM device_fingerprints 
               WHERE customer_id = :cid AND device_hash = :hash"""
        ),
        {"cid": request.customer_id, "hash": device_hash},
    )
    existing = result.fetchone()

    if existing:
        # Update last used
        await db.execute(
            text("UPDATE device_fingerprints SET last_used_at = :now WHERE id = :id"),
            {"now": datetime.utcnow(), "id": existing.id},
        )
        await db.commit()
        return {"device_id": existing.id, "status": "updated", "is_trusted": existing.is_trusted}

    # Create new device
    device = DeviceFingerprint(
        customer_id=request.customer_id,
        device_id=request.device_id,
        device_hash=device_hash,
        device_type=request.device_type,
        os_name=request.os_name,
        os_version=request.os_version,
        browser=request.browser,
        ip_address=request.ip_address,
        location=request.location,
    )

    db.add(device)
    await db.commit()
    await db.refresh(device)

    return {"device_id": device.id, "status": "registered", "is_trusted": False}


@app.put("/api/v1/devices/{device_id}/trust")
async def trust_device(device_id: str, trusted: bool, db: AsyncSession = Depends(get_db)):
    """Mark device as trusted/untrusted"""
    await db.execute(
        text("UPDATE device_fingerprints SET is_trusted = :trusted WHERE id = :id"),
        {"trusted": trusted, "id": device_id},
    )
    await db.commit()
    return {"message": f"Device {'trusted' if trusted else 'untrusted'}"}


@app.get("/api/v1/devices/{customer_id}")
async def list_devices(customer_id: str, db: AsyncSession = Depends(get_db)):
    """List all devices for a customer"""
    result = await db.execute(
        text(
            """SELECT * FROM device_fingerprints 
               WHERE customer_id = :cid 
               ORDER BY last_used_at DESC"""
        ),
        {"cid": customer_id},
    )
    devices = result.fetchall()

    return {
        "devices": [
            {
                "device_id": d.id,
                "device_type": d.device_type,
                "os": f"{d.os_name} {d.os_version}" if d.os_name else None,
                "browser": d.browser,
                "is_trusted": d.is_trusted,
                "last_used": d.last_used_at.isoformat(),
                "registered": d.created_at.isoformat(),
            }
            for d in devices
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
