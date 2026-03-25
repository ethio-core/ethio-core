"""
M3 Card Lifecycle Service - Card Issuance, Activation & Management
Ethiopian Banking Core Platform
"""

import asyncio
import hashlib
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import aiohttp
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, Field, validator
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.responses import Response

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/card_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")
EVENT_STORE_URL = os.getenv("EVENT_STORE_URL", "http://event-store:8000")
IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://m1-identity:8001")
HSM_SERVICE_URL = os.getenv("HSM_SERVICE_URL", "http://hsm-service:8080")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
CARD_BIN_PREFIX = os.getenv("CARD_BIN_PREFIX", "453201")  # Ethiopian bank BIN

# Metrics
card_issued = Counter("card_issued_total", "Total cards issued", ["card_type", "status"])
card_activated = Counter("card_activated_total", "Total cards activated", ["status"])
card_blocked = Counter("card_blocked_total", "Total cards blocked", ["reason"])
pin_operations = Counter("card_pin_operations_total", "PIN operations", ["operation", "status"])
card_operation_latency = Histogram("card_operation_seconds", "Card operation latency", ["operation"])

# Database setup
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20, max_overflow=30)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

security = HTTPBearer()


class CardType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    PREPAID = "prepaid"
    VIRTUAL = "virtual"


class CardStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CardNetwork(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    ETHSWITCH = "ethswitch"
    UNIONPAY = "unionpay"


class BlockReason(str, Enum):
    LOST = "lost"
    STOLEN = "stolen"
    FRAUD = "fraud"
    CUSTOMER_REQUEST = "customer_request"
    COMPLIANCE = "compliance"
    EXPIRED = "expired"
    DAMAGED = "damaged"


# Database Models
class Card(Base):
    __tablename__ = "cards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False, index=True)
    account_id = Column(String(36), nullable=False, index=True)
    card_number_hash = Column(String(128), nullable=False, unique=True)
    card_number_last4 = Column(String(4), nullable=False)
    card_number_encrypted = Column(Text, nullable=False)
    card_type = Column(String(20), nullable=False)
    card_network = Column(String(20), nullable=False)
    expiry_month = Column(Integer, nullable=False)
    expiry_year = Column(Integer, nullable=False)
    cvv_hash = Column(String(128), nullable=False)
    status = Column(String(20), default=CardStatus.PENDING.value)
    daily_limit = Column(Float, default=50000.0)
    monthly_limit = Column(Float, default=500000.0)
    transaction_limit = Column(Float, default=25000.0)
    international_enabled = Column(Boolean, default=False)
    online_enabled = Column(Boolean, default=True)
    contactless_enabled = Column(Boolean, default=True)
    pin_set = Column(Boolean, default=False)
    pin_hash = Column(String(128))
    pin_attempts = Column(Integer, default=0)
    pin_blocked_until = Column(DateTime)
    issued_at = Column(DateTime)
    activated_at = Column(DateTime)
    blocked_at = Column(DateTime)
    block_reason = Column(String(50))
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_card_customer", "customer_id"),
        Index("idx_card_account", "account_id"),
        Index("idx_card_status", "status"),
        Index("idx_card_expiry", "expiry_year", "expiry_month"),
    )


class CardApplication(Base):
    __tablename__ = "card_applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False)
    account_id = Column(String(36), nullable=False)
    card_type = Column(String(20), nullable=False)
    card_network = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")
    rejection_reason = Column(Text)
    card_id = Column(String(36))
    delivery_address = Column(Text)
    delivery_method = Column(String(20), default="branch")
    branch_code = Column(String(10))
    requested_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    rejected_at = Column(DateTime)
    issued_at = Column(DateTime)


class CardTransaction(Base):
    __tablename__ = "card_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String(36), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="ETB")
    merchant_name = Column(String(200))
    merchant_category = Column(String(10))
    terminal_id = Column(String(20))
    authorization_code = Column(String(20))
    status = Column(String(20), default="pending")
    decline_reason = Column(String(100))
    is_international = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_card_txn_date", "created_at"),)


class PINHistory(Base):
    __tablename__ = "pin_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    card_id = Column(String(36), nullable=False, index=True)
    pin_hash = Column(String(128), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(String(36))
    change_reason = Column(String(50))


# Pydantic Models
class CardApplicationRequest(BaseModel):
    customer_id: str
    account_id: str
    card_type: CardType = CardType.DEBIT
    card_network: CardNetwork = CardNetwork.VISA
    delivery_method: str = "branch"
    delivery_address: Optional[str] = None
    branch_code: Optional[str] = None


class CardApplicationResponse(BaseModel):
    application_id: str
    customer_id: str
    status: str
    card_type: str
    card_network: str
    estimated_delivery: Optional[str] = None
    created_at: datetime


class CardResponse(BaseModel):
    card_id: str
    customer_id: str
    card_number_masked: str
    card_type: str
    card_network: str
    status: str
    expiry_date: str
    daily_limit: float
    monthly_limit: float
    international_enabled: bool
    online_enabled: bool
    contactless_enabled: bool
    pin_set: bool
    issued_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None


class CardActivationRequest(BaseModel):
    card_id: str
    customer_id: str
    last4_digits: str
    cvv: str


class SetPINRequest(BaseModel):
    card_id: str
    customer_id: str
    pin: str = Field(..., min_length=4, max_length=6)
    confirm_pin: str = Field(..., min_length=4, max_length=6)

    @validator("confirm_pin")
    def pins_match(cls, v, values):
        if "pin" in values and v != values["pin"]:
            raise ValueError("PINs do not match")
        return v


class ChangePINRequest(BaseModel):
    card_id: str
    customer_id: str
    current_pin: str
    new_pin: str = Field(..., min_length=4, max_length=6)
    confirm_new_pin: str = Field(..., min_length=4, max_length=6)


class VerifyPINRequest(BaseModel):
    card_id: str
    pin: str


class BlockCardRequest(BaseModel):
    card_id: str
    customer_id: str
    reason: BlockReason
    notes: Optional[str] = None


class UpdateLimitsRequest(BaseModel):
    card_id: str
    customer_id: str
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    transaction_limit: Optional[float] = None


class CardSettingsRequest(BaseModel):
    card_id: str
    customer_id: str
    international_enabled: Optional[bool] = None
    online_enabled: Optional[bool] = None
    contactless_enabled: Optional[bool] = None


class AuthorizationRequest(BaseModel):
    card_number: str
    cvv: str
    expiry_month: int
    expiry_year: int
    amount: float
    currency: str = "ETB"
    merchant_name: str
    merchant_category: str
    terminal_id: Optional[str] = None
    is_international: bool = False
    is_online: bool = False


class AuthorizationResponse(BaseModel):
    authorized: bool
    authorization_code: Optional[str] = None
    decline_reason: Optional[str] = None
    available_balance: Optional[float] = None


# Card Generator
class CardGenerator:
    def __init__(self, bin_prefix: str):
        self.bin_prefix = bin_prefix

    def generate_card_number(self) -> str:
        """Generate Luhn-valid card number"""
        # Generate 9 random digits (BIN + 9 + check digit = 16)
        random_digits = "".join([str(secrets.randbelow(10)) for _ in range(9)])
        partial = self.bin_prefix + random_digits

        # Calculate Luhn check digit
        check_digit = self._luhn_checksum(partial)
        return partial + str(check_digit)

    def _luhn_checksum(self, card_number: str) -> int:
        """Calculate Luhn check digit"""

        def digits_of(n):
            return [int(d) for d in str(n)]

        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]

        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))

        return (10 - (checksum % 10)) % 10

    def validate_card_number(self, card_number: str) -> bool:
        """Validate card number using Luhn algorithm"""
        try:
            digits = [int(d) for d in card_number]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]

            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum([int(x) for x in str(d * 2)])

            return checksum % 10 == 0
        except (ValueError, IndexError):
            return False

    def generate_cvv(self) -> str:
        """Generate 3-digit CVV"""
        return "".join([str(secrets.randbelow(10)) for _ in range(3)])

    def generate_expiry(self, years: int = 5) -> tuple[int, int]:
        """Generate expiry date"""
        now = datetime.utcnow()
        expiry_date = now + timedelta(days=365 * years)
        return expiry_date.month, expiry_date.year


# Encryption Service (simplified - use HSM in production)
class CardEncryption:
    def __init__(self, key: str):
        self.key = key.encode()

    def encrypt_card_number(self, card_number: str) -> str:
        """Encrypt card number - use HSM in production"""
        # Simplified encryption - replace with HSM in production
        import base64

        data = card_number.encode()
        # XOR with key (NOT secure - use proper encryption)
        encrypted = bytes([data[i] ^ self.key[i % len(self.key)] for i in range(len(data))])
        return base64.b64encode(encrypted).decode()

    def decrypt_card_number(self, encrypted: str) -> str:
        """Decrypt card number - use HSM in production"""
        import base64

        data = base64.b64decode(encrypted)
        decrypted = bytes([data[i] ^ self.key[i % len(self.key)] for i in range(len(data))])
        return decrypted.decode()

    def hash_pin(self, pin: str, salt: str) -> str:
        """Hash PIN with salt"""
        return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100000).hex()

    def verify_pin(self, pin: str, salt: str, pin_hash: str) -> bool:
        """Verify PIN against hash"""
        return self.hash_pin(pin, salt) == pin_hash


# Event Publisher
class EventPublisher:
    def __init__(self, event_store_url: str):
        self.event_store_url = event_store_url

    async def publish(self, event_type: str, aggregate_id: str, data: dict):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "aggregate_type": "card",
            "aggregate_id": aggregate_id,
            "data": data,
            "metadata": {"service": "m3-card", "version": "1.0.0"},
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
card_generator = CardGenerator(CARD_BIN_PREFIX)
card_encryption = CardEncryption(JWT_SECRET)
event_publisher = EventPublisher(EVENT_STORE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# FastAPI Application
app = FastAPI(
    title="M3 Card Lifecycle Service",
    description="Card Issuance, Activation & Management for Ethiopian Banking",
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
    return {"status": "healthy", "service": "m3-card", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")


# Card Application Endpoints
@app.post("/api/v1/cards/apply", response_model=CardApplicationResponse)
async def apply_for_card(
    request: CardApplicationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Apply for a new card"""
    with card_operation_latency.labels(operation="apply").time():
        # Check for existing pending applications
        result = await db.execute(
            text(
                """SELECT id FROM card_applications 
                   WHERE customer_id = :cid AND account_id = :aid AND status = 'pending'"""
            ),
            {"cid": request.customer_id, "aid": request.account_id},
        )
        if result.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending application already exists for this account",
            )

        # Create application
        application = CardApplication(
            customer_id=request.customer_id,
            account_id=request.account_id,
            card_type=request.card_type.value,
            card_network=request.card_network.value,
            delivery_method=request.delivery_method,
            delivery_address=request.delivery_address,
            branch_code=request.branch_code,
        )

        db.add(application)
        await db.commit()
        await db.refresh(application)

        # Auto-approve for debit cards (simplified)
        if request.card_type == CardType.DEBIT:
            background_tasks.add_task(auto_approve_application, application.id)

        return CardApplicationResponse(
            application_id=application.id,
            customer_id=application.customer_id,
            status=application.status,
            card_type=application.card_type,
            card_network=application.card_network,
            estimated_delivery="5-7 business days" if request.delivery_method == "courier" else "Visit branch",
            created_at=application.requested_at,
        )


async def auto_approve_application(application_id: str):
    """Auto-approve card application and issue card"""
    async with async_session() as db:
        result = await db.execute(
            text("SELECT * FROM card_applications WHERE id = :id"), {"id": application_id}
        )
        app_row = result.fetchone()
        if not app_row:
            return

        # Generate card
        card_number = card_generator.generate_card_number()
        cvv = card_generator.generate_cvv()
        exp_month, exp_year = card_generator.generate_expiry()

        # Create card
        card = Card(
            customer_id=app_row.customer_id,
            account_id=app_row.account_id,
            card_number_hash=hashlib.sha256(card_number.encode()).hexdigest(),
            card_number_last4=card_number[-4:],
            card_number_encrypted=card_encryption.encrypt_card_number(card_number),
            card_type=app_row.card_type,
            card_network=app_row.card_network,
            expiry_month=exp_month,
            expiry_year=exp_year,
            cvv_hash=hashlib.sha256(cvv.encode()).hexdigest(),
            status=CardStatus.PENDING.value,
            expires_at=datetime(exp_year, exp_month, 1) + timedelta(days=31),
            issued_at=datetime.utcnow(),
        )

        db.add(card)

        # Update application
        await db.execute(
            text(
                """UPDATE card_applications 
                   SET status = 'approved', approved_at = :now, issued_at = :now, card_id = :cid 
                   WHERE id = :id"""
            ),
            {"now": datetime.utcnow(), "cid": card.id, "id": application_id},
        )

        await db.commit()

        card_issued.labels(card_type=app_row.card_type, status="success").inc()

        # Publish event
        await event_publisher.publish(
            "CardIssued",
            card.id,
            {
                "customer_id": card.customer_id,
                "card_type": card.card_type,
                "last4": card.card_number_last4,
            },
        )


# Card Management Endpoints
@app.get("/api/v1/cards/{customer_id}", response_model=list[CardResponse])
async def get_customer_cards(customer_id: str, db: AsyncSession = Depends(get_db)):
    """Get all cards for a customer"""
    result = await db.execute(
        text("SELECT * FROM cards WHERE customer_id = :cid ORDER BY created_at DESC"),
        {"cid": customer_id},
    )
    cards = result.fetchall()

    return [
        CardResponse(
            card_id=card.id,
            customer_id=card.customer_id,
            card_number_masked=f"****-****-****-{card.card_number_last4}",
            card_type=card.card_type,
            card_network=card.card_network,
            status=card.status,
            expiry_date=f"{card.expiry_month:02d}/{card.expiry_year}",
            daily_limit=card.daily_limit,
            monthly_limit=card.monthly_limit,
            international_enabled=card.international_enabled,
            online_enabled=card.online_enabled,
            contactless_enabled=card.contactless_enabled,
            pin_set=card.pin_set,
            issued_at=card.issued_at,
            activated_at=card.activated_at,
        )
        for card in cards
    ]


@app.post("/api/v1/cards/activate")
async def activate_card(
    request: CardActivationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Activate a card"""
    with card_operation_latency.labels(operation="activate").time():
        result = await db.execute(
            text("SELECT * FROM cards WHERE id = :id AND customer_id = :cid"),
            {"id": request.card_id, "cid": request.customer_id},
        )
        card = result.fetchone()

        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

        if card.status != CardStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Card cannot be activated. Current status: {card.status}",
            )

        # Verify last 4 digits
        if card.card_number_last4 != request.last4_digits:
            card_activated.labels(status="invalid_digits").inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid card details")

        # Verify CVV
        if hashlib.sha256(request.cvv.encode()).hexdigest() != card.cvv_hash:
            card_activated.labels(status="invalid_cvv").inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid CVV")

        # Activate card
        await db.execute(
            text("UPDATE cards SET status = :status, activated_at = :now WHERE id = :id"),
            {"status": CardStatus.ACTIVE.value, "now": datetime.utcnow(), "id": request.card_id},
        )
        await db.commit()

        card_activated.labels(status="success").inc()

        background_tasks.add_task(
            event_publisher.publish,
            "CardActivated",
            request.card_id,
            {"customer_id": request.customer_id},
        )

        return {"message": "Card activated successfully", "card_id": request.card_id}


# PIN Management
@app.post("/api/v1/cards/pin/set")
async def set_pin(
    request: SetPINRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Set PIN for a card"""
    with card_operation_latency.labels(operation="set_pin").time():
        result = await db.execute(
            text("SELECT * FROM cards WHERE id = :id AND customer_id = :cid"),
            {"id": request.card_id, "cid": request.customer_id},
        )
        card = result.fetchone()

        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

        if card.pin_set:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PIN already set. Use change PIN endpoint.",
            )

        # Hash PIN
        pin_hash = card_encryption.hash_pin(request.pin, request.card_id)

        # Update card
        await db.execute(
            text("UPDATE cards SET pin_hash = :hash, pin_set = true WHERE id = :id"),
            {"hash": pin_hash, "id": request.card_id},
        )

        # Add to PIN history
        pin_history = PINHistory(
            card_id=request.card_id,
            pin_hash=pin_hash,
            changed_by=request.customer_id,
            change_reason="initial_set",
        )
        db.add(pin_history)

        await db.commit()

        pin_operations.labels(operation="set", status="success").inc()

        background_tasks.add_task(
            event_publisher.publish,
            "CardPINSet",
            request.card_id,
            {"customer_id": request.customer_id},
        )

        return {"message": "PIN set successfully"}


@app.post("/api/v1/cards/pin/change")
async def change_pin(
    request: ChangePINRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Change card PIN"""
    with card_operation_latency.labels(operation="change_pin").time():
        result = await db.execute(
            text("SELECT * FROM cards WHERE id = :id AND customer_id = :cid"),
            {"id": request.card_id, "cid": request.customer_id},
        )
        card = result.fetchone()

        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

        if not card.pin_set:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN not set")

        # Verify current PIN
        if not card_encryption.verify_pin(request.current_pin, request.card_id, card.pin_hash):
            pin_operations.labels(operation="change", status="invalid_current").inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current PIN")

        # Validate new PIN matches confirmation
        if request.new_pin != request.confirm_new_pin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New PINs do not match")

        # Check PIN not same as current
        if request.new_pin == request.current_pin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New PIN must be different from current PIN",
            )

        # Hash new PIN
        new_pin_hash = card_encryption.hash_pin(request.new_pin, request.card_id)

        # Update card
        await db.execute(
            text("UPDATE cards SET pin_hash = :hash, pin_attempts = 0 WHERE id = :id"),
            {"hash": new_pin_hash, "id": request.card_id},
        )

        # Add to PIN history
        pin_history = PINHistory(
            card_id=request.card_id,
            pin_hash=new_pin_hash,
            changed_by=request.customer_id,
            change_reason="customer_change",
        )
        db.add(pin_history)

        await db.commit()

        pin_operations.labels(operation="change", status="success").inc()

        background_tasks.add_task(
            event_publisher.publish,
            "CardPINChanged",
            request.card_id,
            {"customer_id": request.customer_id},
        )

        return {"message": "PIN changed successfully"}


@app.post("/api/v1/cards/pin/verify")
async def verify_pin(request: VerifyPINRequest, db: AsyncSession = Depends(get_db)):
    """Verify card PIN"""
    result = await db.execute(text("SELECT * FROM cards WHERE id = :id"), {"id": request.card_id})
    card = result.fetchone()

    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    if not card.pin_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN not set")

    # Check if PIN is blocked
    if card.pin_blocked_until and datetime.utcnow() < card.pin_blocked_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PIN blocked until {card.pin_blocked_until}",
        )

    # Verify PIN
    if not card_encryption.verify_pin(request.pin, request.card_id, card.pin_hash):
        # Increment attempts
        new_attempts = card.pin_attempts + 1

        if new_attempts >= 3:
            # Block PIN for 24 hours
            await db.execute(
                text(
                    "UPDATE cards SET pin_attempts = :attempts, pin_blocked_until = :blocked WHERE id = :id"
                ),
                {
                    "attempts": new_attempts,
                    "blocked": datetime.utcnow() + timedelta(hours=24),
                    "id": request.card_id,
                },
            )
            await db.commit()
            pin_operations.labels(operation="verify", status="blocked").inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN blocked due to too many attempts")

        await db.execute(
            text("UPDATE cards SET pin_attempts = :attempts WHERE id = :id"),
            {"attempts": new_attempts, "id": request.card_id},
        )
        await db.commit()

        pin_operations.labels(operation="verify", status="invalid").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid PIN. {3 - new_attempts} attempts remaining.",
        )

    # Reset attempts on success
    await db.execute(
        text("UPDATE cards SET pin_attempts = 0 WHERE id = :id"), {"id": request.card_id}
    )
    await db.commit()

    pin_operations.labels(operation="verify", status="success").inc()
    return {"valid": True}


# Card Control Endpoints
@app.post("/api/v1/cards/block")
async def block_card(
    request: BlockCardRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Block a card"""
    with card_operation_latency.labels(operation="block").time():
        result = await db.execute(
            text("SELECT * FROM cards WHERE id = :id AND customer_id = :cid"),
            {"id": request.card_id, "cid": request.customer_id},
        )
        card = result.fetchone()

        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

        if card.status == CardStatus.BLOCKED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Card already blocked")

        await db.execute(
            text(
                """UPDATE cards 
                   SET status = :status, blocked_at = :now, block_reason = :reason 
                   WHERE id = :id"""
            ),
            {
                "status": CardStatus.BLOCKED.value,
                "now": datetime.utcnow(),
                "reason": request.reason.value,
                "id": request.card_id,
            },
        )
        await db.commit()

        card_blocked.labels(reason=request.reason.value).inc()

        background_tasks.add_task(
            event_publisher.publish,
            "CardBlocked",
            request.card_id,
            {"customer_id": request.customer_id, "reason": request.reason.value},
        )

        return {"message": "Card blocked successfully", "card_id": request.card_id}


@app.post("/api/v1/cards/unblock")
async def unblock_card(
    card_id: str,
    customer_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Unblock a card"""
    result = await db.execute(
        text("SELECT * FROM cards WHERE id = :id AND customer_id = :cid"),
        {"id": card_id, "cid": customer_id},
    )
    card = result.fetchone()

    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    if card.status != CardStatus.BLOCKED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Card is not blocked")

    # Cannot unblock if lost/stolen
    if card.block_reason in [BlockReason.LOST.value, BlockReason.STOLEN.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unblock lost/stolen card. Please request new card.",
        )

    await db.execute(
        text(
            "UPDATE cards SET status = :status, blocked_at = NULL, block_reason = NULL WHERE id = :id"
        ),
        {"status": CardStatus.ACTIVE.value, "id": card_id},
    )
    await db.commit()

    background_tasks.add_task(
        event_publisher.publish, "CardUnblocked", card_id, {"customer_id": customer_id}
    )

    return {"message": "Card unblocked successfully"}


@app.put("/api/v1/cards/limits")
async def update_limits(request: UpdateLimitsRequest, db: AsyncSession = Depends(get_db)):
    """Update card limits"""
    result = await db.execute(
        text("SELECT * FROM cards WHERE id = :id AND customer_id = :cid"),
        {"id": request.card_id, "cid": request.customer_id},
    )
    card = result.fetchone()

    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    updates = []
    params = {"id": request.card_id}

    if request.daily_limit is not None:
        updates.append("daily_limit = :daily")
        params["daily"] = request.daily_limit

    if request.monthly_limit is not None:
        updates.append("monthly_limit = :monthly")
        params["monthly"] = request.monthly_limit

    if request.transaction_limit is not None:
        updates.append("transaction_limit = :txn")
        params["txn"] = request.transaction_limit

    if updates:
        await db.execute(text(f"UPDATE cards SET {', '.join(updates)} WHERE id = :id"), params)
        await db.commit()

    return {"message": "Limits updated successfully"}


@app.put("/api/v1/cards/settings")
async def update_settings(request: CardSettingsRequest, db: AsyncSession = Depends(get_db)):
    """Update card settings"""
    result = await db.execute(
        text("SELECT * FROM cards WHERE id = :id AND customer_id = :cid"),
        {"id": request.card_id, "cid": request.customer_id},
    )
    card = result.fetchone()

    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    updates = []
    params = {"id": request.card_id}

    if request.international_enabled is not None:
        updates.append("international_enabled = :intl")
        params["intl"] = request.international_enabled

    if request.online_enabled is not None:
        updates.append("online_enabled = :online")
        params["online"] = request.online_enabled

    if request.contactless_enabled is not None:
        updates.append("contactless_enabled = :contactless")
        params["contactless"] = request.contactless_enabled

    if updates:
        await db.execute(text(f"UPDATE cards SET {', '.join(updates)} WHERE id = :id"), params)
        await db.commit()

    return {"message": "Settings updated successfully"}


# Authorization Endpoint (for transaction processing)
@app.post("/api/v1/cards/authorize", response_model=AuthorizationResponse)
async def authorize_transaction(
    request: AuthorizationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Authorize a card transaction"""
    with card_operation_latency.labels(operation="authorize").time():
        # Find card by number hash
        card_hash = hashlib.sha256(request.card_number.encode()).hexdigest()
        result = await db.execute(
            text("SELECT * FROM cards WHERE card_number_hash = :hash"), {"hash": card_hash}
        )
        card = result.fetchone()

        if not card:
            return AuthorizationResponse(authorized=False, decline_reason="Card not found")

        # Validate card status
        if card.status != CardStatus.ACTIVE.value:
            return AuthorizationResponse(authorized=False, decline_reason=f"Card {card.status}")

        # Validate expiry
        if request.expiry_month != card.expiry_month or request.expiry_year != card.expiry_year:
            return AuthorizationResponse(authorized=False, decline_reason="Invalid expiry date")

        # Validate CVV
        if hashlib.sha256(request.cvv.encode()).hexdigest() != card.cvv_hash:
            return AuthorizationResponse(authorized=False, decline_reason="Invalid CVV")

        # Check limits
        if request.amount > card.transaction_limit:
            return AuthorizationResponse(
                authorized=False, decline_reason="Transaction limit exceeded"
            )

        # Check international
        if request.is_international and not card.international_enabled:
            return AuthorizationResponse(
                authorized=False, decline_reason="International transactions disabled"
            )

        # Check online
        if request.is_online and not card.online_enabled:
            return AuthorizationResponse(
                authorized=False, decline_reason="Online transactions disabled"
            )

        # Generate authorization code
        auth_code = secrets.token_hex(6).upper()

        # Record transaction
        txn = CardTransaction(
            card_id=card.id,
            transaction_type="purchase",
            amount=request.amount,
            currency=request.currency,
            merchant_name=request.merchant_name,
            merchant_category=request.merchant_category,
            terminal_id=request.terminal_id,
            authorization_code=auth_code,
            status="authorized",
            is_international=request.is_international,
            is_online=request.is_online,
        )
        db.add(txn)
        await db.commit()

        background_tasks.add_task(
            event_publisher.publish,
            "CardTransactionAuthorized",
            card.id,
            {
                "amount": request.amount,
                "merchant": request.merchant_name,
                "authorization_code": auth_code,
            },
        )

        return AuthorizationResponse(authorized=True, authorization_code=auth_code)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
