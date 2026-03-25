"""
M4 Transaction Service - Core Banking Transactions with Saga Orchestration
Ethiopian Banking Core Platform
"""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

import aiohttp
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from pydantic import BaseModel, Field, validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.responses import Response

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/transaction_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/3")
EVENT_STORE_URL = os.getenv("EVENT_STORE_URL", "http://event-store:8000")
CARD_SERVICE_URL = os.getenv("CARD_SERVICE_URL", "http://m3-card:8003")
SECURITY_SERVICE_URL = os.getenv("SECURITY_SERVICE_URL", "http://m5-security:8005")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")

# Ethiopian specific limits (in ETB)
DAILY_TRANSFER_LIMIT = float(os.getenv("DAILY_TRANSFER_LIMIT", "200000"))
SINGLE_TRANSFER_LIMIT = float(os.getenv("SINGLE_TRANSFER_LIMIT", "50000"))
ATM_DAILY_LIMIT = float(os.getenv("ATM_DAILY_LIMIT", "30000"))

# Metrics
transactions_total = Counter("transactions_total", "Total transactions", ["type", "status"])
transaction_amount = Histogram(
    "transaction_amount_etb",
    "Transaction amounts in ETB",
    ["type"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 500000],
)
transaction_latency = Histogram("transaction_latency_seconds", "Transaction processing latency", ["type"])
active_sagas = Gauge("active_sagas", "Currently active saga transactions")
failed_compensations = Counter("failed_compensations_total", "Failed compensation transactions")

# Database setup
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=30, max_overflow=50)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

security = HTTPBearer()


class TransactionType(str, Enum):
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PAYMENT = "payment"
    BILL_PAYMENT = "bill_payment"
    AIRTIME = "airtime"
    ATM = "atm"
    POS = "pos"
    REVERSAL = "reversal"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    CANCELLED = "cancelled"


class SagaStatus(str, Enum):
    STARTED = "started"
    EXECUTING = "executing"
    COMPENSATING = "compensating"
    COMPLETED = "completed"
    FAILED = "failed"


class Currency(str, Enum):
    ETB = "ETB"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


# Database Models
class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String(36), nullable=False, index=True)
    account_number = Column(String(20), unique=True, nullable=False)
    account_type = Column(String(20), nullable=False)  # savings, checking, business
    currency = Column(String(3), default="ETB")
    balance = Column(Numeric(18, 2), default=0)
    available_balance = Column(Numeric(18, 2), default=0)
    hold_amount = Column(Numeric(18, 2), default=0)
    daily_limit = Column(Numeric(18, 2), default=DAILY_TRANSFER_LIMIT)
    status = Column(String(20), default="active")
    is_primary = Column(Boolean, default=False)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_account_customer", "customer_id"),
        Index("idx_account_number", "account_number"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_number = Column(String(30), unique=True, nullable=False)
    transaction_type = Column(String(20), nullable=False)
    source_account_id = Column(String(36), index=True)
    destination_account_id = Column(String(36), index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), default="ETB")
    fee = Column(Numeric(18, 2), default=0)
    exchange_rate = Column(Numeric(12, 6))
    status = Column(String(20), default=TransactionStatus.PENDING.value)
    description = Column(Text)
    metadata = Column(Text)  # JSON string
    error_message = Column(Text)
    channel = Column(String(20))  # mobile, web, atm, pos, branch
    device_id = Column(String(100))
    ip_address = Column(String(45))
    location = Column(String(200))
    initiated_by = Column(String(36))
    approved_by = Column(String(36))
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    reversed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_txn_reference", "reference_number"),
        Index("idx_txn_source", "source_account_id"),
        Index("idx_txn_dest", "destination_account_id"),
        Index("idx_txn_date", "created_at"),
        Index("idx_txn_status", "status"),
    )


class SagaTransaction(Base):
    __tablename__ = "saga_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String(36), nullable=False, index=True)
    saga_type = Column(String(50), nullable=False)
    status = Column(String(20), default=SagaStatus.STARTED.value)
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, nullable=False)
    steps_data = Column(Text)  # JSON
    compensation_data = Column(Text)  # JSON
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class TransactionHold(Base):
    __tablename__ = "transaction_holds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), nullable=False, index=True)
    transaction_id = Column(String(36), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    reason = Column(String(100))
    status = Column(String(20), default="active")
    expires_at = Column(DateTime)
    released_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyLimit(Base):
    __tablename__ = "daily_limits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)
    date = Column(DateTime, nullable=False)
    total_amount = Column(Numeric(18, 2), default=0)
    transaction_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("idx_daily_limit", "account_id", "transaction_type", "date"),)


# Pydantic Models
class TransferRequest(BaseModel):
    source_account_id: str
    destination_account_number: str
    amount: float = Field(..., gt=0)
    currency: Currency = Currency.ETB
    description: Optional[str] = None
    channel: str = "api"
    device_id: Optional[str] = None
    ip_address: Optional[str] = None

    @validator("amount")
    def validate_amount(cls, v):
        if v > SINGLE_TRANSFER_LIMIT:
            raise ValueError(f"Amount exceeds single transfer limit of {SINGLE_TRANSFER_LIMIT} ETB")
        return v


class TransferResponse(BaseModel):
    transaction_id: str
    reference_number: str
    status: str
    amount: float
    fee: float
    source_account: str
    destination_account: str
    completed_at: Optional[datetime] = None


class DepositRequest(BaseModel):
    account_id: str
    amount: float = Field(..., gt=0)
    currency: Currency = Currency.ETB
    channel: str = "branch"
    depositor_name: Optional[str] = None
    depositor_id: Optional[str] = None
    description: Optional[str] = None


class WithdrawalRequest(BaseModel):
    account_id: str
    amount: float = Field(..., gt=0)
    currency: Currency = Currency.ETB
    channel: str = "branch"
    description: Optional[str] = None


class BillPaymentRequest(BaseModel):
    account_id: str
    biller_code: str
    bill_number: str
    amount: float = Field(..., gt=0)
    customer_reference: Optional[str] = None


class AirtimeRequest(BaseModel):
    account_id: str
    phone_number: str
    amount: float = Field(..., gt=0, le=5000)
    operator: str  # ethio_telecom, safaricom


class BalanceResponse(BaseModel):
    account_id: str
    account_number: str
    balance: float
    available_balance: float
    hold_amount: float
    currency: str
    as_of: datetime


class StatementRequest(BaseModel):
    account_id: str
    start_date: datetime
    end_date: datetime
    page: int = 1
    page_size: int = 50


class TransactionResponse(BaseModel):
    transaction_id: str
    reference_number: str
    transaction_type: str
    amount: float
    fee: float
    currency: str
    status: str
    description: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# Saga Orchestrator
class SagaOrchestrator:
    def __init__(self):
        self.steps = []
        self.compensations = []

    async def execute_transfer_saga(
        self,
        db: AsyncSession,
        source_account_id: str,
        dest_account_id: str,
        amount: Decimal,
        fee: Decimal,
        transaction_id: str,
    ) -> bool:
        """Execute transfer with saga pattern for consistency"""
        saga = SagaTransaction(
            transaction_id=transaction_id,
            saga_type="transfer",
            total_steps=4,
        )
        db.add(saga)
        await db.commit()

        active_sagas.inc()

        try:
            # Step 1: Validate source account
            saga.current_step = 1
            await db.commit()

            source = await self._get_account(db, source_account_id)
            if not source or source.status != "active":
                raise ValueError("Source account invalid or inactive")

            if source.available_balance < amount + fee:
                raise ValueError("Insufficient funds")

            # Step 2: Create hold on source account
            saga.current_step = 2
            await db.commit()

            hold = TransactionHold(
                account_id=source_account_id,
                transaction_id=transaction_id,
                amount=amount + fee,
                reason="transfer_hold",
                expires_at=datetime.utcnow() + timedelta(minutes=5),
            )
            db.add(hold)

            await db.execute(
                text(
                    """UPDATE accounts 
                       SET available_balance = available_balance - :amount,
                           hold_amount = hold_amount + :amount
                       WHERE id = :id"""
                ),
                {"amount": float(amount + fee), "id": source_account_id},
            )
            await db.commit()

            # Step 3: Credit destination account
            saga.current_step = 3
            await db.commit()

            dest = await self._get_account(db, dest_account_id)
            if not dest or dest.status != "active":
                raise ValueError("Destination account invalid or inactive")

            await db.execute(
                text(
                    """UPDATE accounts 
                       SET balance = balance + :amount,
                           available_balance = available_balance + :amount
                       WHERE id = :id"""
                ),
                {"amount": float(amount), "id": dest_account_id},
            )
            await db.commit()

            # Step 4: Complete debit from source
            saga.current_step = 4
            await db.commit()

            await db.execute(
                text(
                    """UPDATE accounts 
                       SET balance = balance - :amount,
                           hold_amount = hold_amount - :amount
                       WHERE id = :id"""
                ),
                {"amount": float(amount + fee), "id": source_account_id},
            )

            # Release hold
            await db.execute(
                text("UPDATE transaction_holds SET status = 'released', released_at = :now WHERE id = :id"),
                {"now": datetime.utcnow(), "id": hold.id},
            )

            saga.status = SagaStatus.COMPLETED.value
            saga.completed_at = datetime.utcnow()
            await db.commit()

            active_sagas.dec()
            return True

        except Exception as e:
            # Compensate
            await self._compensate_transfer(db, saga, source_account_id, dest_account_id, amount, fee)
            saga.status = SagaStatus.FAILED.value
            saga.error_message = str(e)
            await db.commit()
            active_sagas.dec()
            raise

    async def _compensate_transfer(
        self,
        db: AsyncSession,
        saga: SagaTransaction,
        source_account_id: str,
        dest_account_id: str,
        amount: Decimal,
        fee: Decimal,
    ):
        """Compensate failed transfer"""
        saga.status = SagaStatus.COMPENSATING.value
        await db.commit()

        try:
            current_step = saga.current_step

            # Compensate based on how far we got
            if current_step >= 3:
                # Reverse credit to destination
                await db.execute(
                    text(
                        """UPDATE accounts 
                           SET balance = balance - :amount,
                               available_balance = available_balance - :amount
                           WHERE id = :id"""
                    ),
                    {"amount": float(amount), "id": dest_account_id},
                )

            if current_step >= 2:
                # Release hold and restore available balance
                await db.execute(
                    text(
                        """UPDATE accounts 
                           SET available_balance = available_balance + :amount,
                               hold_amount = hold_amount - :amount
                           WHERE id = :id"""
                    ),
                    {"amount": float(amount + fee), "id": source_account_id},
                )

                # Mark holds as cancelled
                await db.execute(
                    text(
                        """UPDATE transaction_holds 
                           SET status = 'cancelled' 
                           WHERE transaction_id = :tid"""
                    ),
                    {"tid": saga.transaction_id},
                )

            await db.commit()

        except Exception as e:
            failed_compensations.inc()
            print(f"Compensation failed: {e}")

    async def _get_account(self, db: AsyncSession, account_id: str):
        result = await db.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": account_id})
        return result.fetchone()


# Fee Calculator
class FeeCalculator:
    FEE_STRUCTURE = {
        TransactionType.TRANSFER: {
            "internal": {"rate": 0.0, "min": 0, "max": 0},
            "external": {"rate": 0.005, "min": 5, "max": 100},
        },
        TransactionType.WITHDRAWAL: {"rate": 0.01, "min": 10, "max": 200},
        TransactionType.ATM: {"own_bank": 0, "other_bank": 25},
        TransactionType.BILL_PAYMENT: {"rate": 0.002, "min": 2, "max": 50},
        TransactionType.AIRTIME: {"rate": 0.0, "min": 0, "max": 0},
    }

    @classmethod
    def calculate(cls, txn_type: TransactionType, amount: float, **kwargs) -> float:
        """Calculate transaction fee"""
        if txn_type == TransactionType.TRANSFER:
            is_internal = kwargs.get("is_internal", True)
            key = "internal" if is_internal else "external"
            fee_config = cls.FEE_STRUCTURE[txn_type][key]
            calculated = amount * fee_config["rate"]
            return max(fee_config["min"], min(calculated, fee_config["max"]))

        elif txn_type == TransactionType.ATM:
            is_own_bank = kwargs.get("is_own_bank", True)
            return cls.FEE_STRUCTURE[txn_type]["own_bank" if is_own_bank else "other_bank"]

        elif txn_type in cls.FEE_STRUCTURE:
            fee_config = cls.FEE_STRUCTURE[txn_type]
            if isinstance(fee_config, dict) and "rate" in fee_config:
                calculated = amount * fee_config["rate"]
                return max(fee_config["min"], min(calculated, fee_config["max"]))

        return 0.0


# Reference Number Generator
class ReferenceGenerator:
    @staticmethod
    def generate(prefix: str = "TXN") -> str:
        """Generate unique reference number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = uuid.uuid4().hex[:8].upper()
        return f"{prefix}{timestamp}{random_part}"


# Event Publisher
class EventPublisher:
    def __init__(self, event_store_url: str):
        self.event_store_url = event_store_url

    async def publish(self, event_type: str, aggregate_id: str, data: dict):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "aggregate_type": "transaction",
            "aggregate_id": aggregate_id,
            "data": data,
            "metadata": {"service": "m4-transaction", "version": "1.0.0"},
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
saga_orchestrator = SagaOrchestrator()
event_publisher = EventPublisher(EVENT_STORE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# FastAPI Application
app = FastAPI(
    title="M4 Transaction Service",
    description="Core Banking Transactions with Saga Orchestration",
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
    return {"status": "healthy", "service": "m4-transaction", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")


# Account Endpoints
@app.get("/api/v1/accounts/{account_id}/balance", response_model=BalanceResponse)
async def get_balance(account_id: str, db: AsyncSession = Depends(get_db)):
    """Get account balance"""
    result = await db.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": account_id})
    account = result.fetchone()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    return BalanceResponse(
        account_id=account.id,
        account_number=account.account_number,
        balance=float(account.balance),
        available_balance=float(account.available_balance),
        hold_amount=float(account.hold_amount),
        currency=account.currency,
        as_of=datetime.utcnow(),
    )


@app.get("/api/v1/accounts/{customer_id}/all")
async def get_customer_accounts(customer_id: str, db: AsyncSession = Depends(get_db)):
    """Get all accounts for a customer"""
    result = await db.execute(
        text("SELECT * FROM accounts WHERE customer_id = :cid ORDER BY is_primary DESC, created_at"),
        {"cid": customer_id},
    )
    accounts = result.fetchall()

    return [
        {
            "account_id": acc.id,
            "account_number": acc.account_number,
            "account_type": acc.account_type,
            "currency": acc.currency,
            "balance": float(acc.balance),
            "available_balance": float(acc.available_balance),
            "status": acc.status,
            "is_primary": acc.is_primary,
        }
        for acc in accounts
    ]


# Transfer Endpoint
@app.post("/api/v1/transactions/transfer", response_model=TransferResponse)
async def transfer(
    request: TransferRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Execute fund transfer"""
    with transaction_latency.labels(type="transfer").time():
        # Get source account
        source_result = await db.execute(
            text("SELECT * FROM accounts WHERE id = :id"), {"id": request.source_account_id}
        )
        source = source_result.fetchone()

        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source account not found")

        if source.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source account is not active")

        # Get destination account
        dest_result = await db.execute(
            text("SELECT * FROM accounts WHERE account_number = :num"),
            {"num": request.destination_account_number},
        )
        dest = dest_result.fetchone()

        if not dest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Destination account not found"
            )

        # Check daily limit
        today = datetime.utcnow().date()
        limit_result = await db.execute(
            text(
                """SELECT COALESCE(SUM(amount), 0) as total 
                   FROM transactions 
                   WHERE source_account_id = :id 
                   AND transaction_type = 'transfer'
                   AND DATE(created_at) = :date
                   AND status = 'completed'"""
            ),
            {"id": request.source_account_id, "date": today},
        )
        daily_total = float(limit_result.fetchone()[0])

        if daily_total + request.amount > DAILY_TRANSFER_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Daily transfer limit exceeded. Remaining: {DAILY_TRANSFER_LIMIT - daily_total} ETB",
            )

        # Calculate fee
        is_internal = True  # Simplified - check bank code in production
        fee = FeeCalculator.calculate(TransactionType.TRANSFER, request.amount, is_internal=is_internal)

        # Check balance
        amount = Decimal(str(request.amount))
        fee_decimal = Decimal(str(fee))

        if Decimal(str(source.available_balance)) < amount + fee_decimal:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

        # Create transaction record
        reference = ReferenceGenerator.generate("TRF")
        transaction = Transaction(
            reference_number=reference,
            transaction_type=TransactionType.TRANSFER.value,
            source_account_id=request.source_account_id,
            destination_account_id=dest.id,
            amount=amount,
            currency=request.currency.value,
            fee=fee_decimal,
            description=request.description,
            channel=request.channel,
            device_id=request.device_id,
            ip_address=request.ip_address,
            status=TransactionStatus.PROCESSING.value,
        )

        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        try:
            # Execute saga
            await saga_orchestrator.execute_transfer_saga(
                db, request.source_account_id, dest.id, amount, fee_decimal, transaction.id
            )

            # Update transaction status
            await db.execute(
                text("UPDATE transactions SET status = :status, completed_at = :now WHERE id = :id"),
                {"status": TransactionStatus.COMPLETED.value, "now": datetime.utcnow(), "id": transaction.id},
            )
            await db.commit()

            transactions_total.labels(type="transfer", status="completed").inc()
            transaction_amount.labels(type="transfer").observe(float(amount))

            # Publish event
            background_tasks.add_task(
                event_publisher.publish,
                "TransferCompleted",
                transaction.id,
                {
                    "reference": reference,
                    "amount": float(amount),
                    "source": source.account_number,
                    "destination": request.destination_account_number,
                },
            )

            return TransferResponse(
                transaction_id=transaction.id,
                reference_number=reference,
                status="completed",
                amount=float(amount),
                fee=fee,
                source_account=source.account_number,
                destination_account=request.destination_account_number,
                completed_at=datetime.utcnow(),
            )

        except Exception as e:
            await db.execute(
                text("UPDATE transactions SET status = :status, error_message = :err WHERE id = :id"),
                {"status": TransactionStatus.FAILED.value, "err": str(e), "id": transaction.id},
            )
            await db.commit()

            transactions_total.labels(type="transfer", status="failed").inc()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Deposit Endpoint
@app.post("/api/v1/transactions/deposit", response_model=TransactionResponse)
async def deposit(
    request: DepositRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Process deposit"""
    with transaction_latency.labels(type="deposit").time():
        # Get account
        result = await db.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": request.account_id})
        account = result.fetchone()

        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        if account.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is not active")

        amount = Decimal(str(request.amount))
        reference = ReferenceGenerator.generate("DEP")

        # Create transaction
        transaction = Transaction(
            reference_number=reference,
            transaction_type=TransactionType.DEPOSIT.value,
            destination_account_id=request.account_id,
            amount=amount,
            currency=request.currency.value,
            description=request.description or f"Deposit by {request.depositor_name or 'Customer'}",
            channel=request.channel,
            status=TransactionStatus.PROCESSING.value,
        )

        db.add(transaction)
        await db.commit()

        # Credit account
        await db.execute(
            text(
                """UPDATE accounts 
                   SET balance = balance + :amount,
                       available_balance = available_balance + :amount
                   WHERE id = :id"""
            ),
            {"amount": float(amount), "id": request.account_id},
        )

        await db.execute(
            text("UPDATE transactions SET status = :status, completed_at = :now WHERE id = :id"),
            {"status": TransactionStatus.COMPLETED.value, "now": datetime.utcnow(), "id": transaction.id},
        )

        await db.commit()

        transactions_total.labels(type="deposit", status="completed").inc()
        transaction_amount.labels(type="deposit").observe(float(amount))

        background_tasks.add_task(
            event_publisher.publish,
            "DepositCompleted",
            transaction.id,
            {"reference": reference, "amount": float(amount), "account": account.account_number},
        )

        return TransactionResponse(
            transaction_id=transaction.id,
            reference_number=reference,
            transaction_type="deposit",
            amount=float(amount),
            fee=0,
            currency=request.currency.value,
            status="completed",
            description=transaction.description,
            created_at=transaction.created_at,
            completed_at=datetime.utcnow(),
        )


# Withdrawal Endpoint
@app.post("/api/v1/transactions/withdrawal", response_model=TransactionResponse)
async def withdrawal(
    request: WithdrawalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Process withdrawal"""
    with transaction_latency.labels(type="withdrawal").time():
        # Get account
        result = await db.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": request.account_id})
        account = result.fetchone()

        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        if account.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is not active")

        amount = Decimal(str(request.amount))
        fee = Decimal(str(FeeCalculator.calculate(TransactionType.WITHDRAWAL, request.amount)))

        if Decimal(str(account.available_balance)) < amount + fee:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

        reference = ReferenceGenerator.generate("WDR")

        # Create transaction
        transaction = Transaction(
            reference_number=reference,
            transaction_type=TransactionType.WITHDRAWAL.value,
            source_account_id=request.account_id,
            amount=amount,
            fee=fee,
            currency=request.currency.value,
            description=request.description or "Cash withdrawal",
            channel=request.channel,
            status=TransactionStatus.PROCESSING.value,
        )

        db.add(transaction)
        await db.commit()

        # Debit account
        await db.execute(
            text(
                """UPDATE accounts 
                   SET balance = balance - :amount,
                       available_balance = available_balance - :amount
                   WHERE id = :id"""
            ),
            {"amount": float(amount + fee), "id": request.account_id},
        )

        await db.execute(
            text("UPDATE transactions SET status = :status, completed_at = :now WHERE id = :id"),
            {"status": TransactionStatus.COMPLETED.value, "now": datetime.utcnow(), "id": transaction.id},
        )

        await db.commit()

        transactions_total.labels(type="withdrawal", status="completed").inc()
        transaction_amount.labels(type="withdrawal").observe(float(amount))

        background_tasks.add_task(
            event_publisher.publish,
            "WithdrawalCompleted",
            transaction.id,
            {"reference": reference, "amount": float(amount), "fee": float(fee)},
        )

        return TransactionResponse(
            transaction_id=transaction.id,
            reference_number=reference,
            transaction_type="withdrawal",
            amount=float(amount),
            fee=float(fee),
            currency=request.currency.value,
            status="completed",
            description=transaction.description,
            created_at=transaction.created_at,
            completed_at=datetime.utcnow(),
        )


# Bill Payment Endpoint
@app.post("/api/v1/transactions/bill-payment", response_model=TransactionResponse)
async def pay_bill(
    request: BillPaymentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Process bill payment"""
    with transaction_latency.labels(type="bill_payment").time():
        # Get account
        result = await db.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": request.account_id})
        account = result.fetchone()

        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        amount = Decimal(str(request.amount))
        fee = Decimal(str(FeeCalculator.calculate(TransactionType.BILL_PAYMENT, request.amount)))

        if Decimal(str(account.available_balance)) < amount + fee:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

        reference = ReferenceGenerator.generate("BIL")

        # Create transaction
        transaction = Transaction(
            reference_number=reference,
            transaction_type=TransactionType.BILL_PAYMENT.value,
            source_account_id=request.account_id,
            amount=amount,
            fee=fee,
            description=f"Bill payment to {request.biller_code} - {request.bill_number}",
            metadata=f'{{"biller_code": "{request.biller_code}", "bill_number": "{request.bill_number}"}}',
            status=TransactionStatus.PROCESSING.value,
        )

        db.add(transaction)
        await db.commit()

        # Debit account
        await db.execute(
            text(
                """UPDATE accounts 
                   SET balance = balance - :amount,
                       available_balance = available_balance - :amount
                   WHERE id = :id"""
            ),
            {"amount": float(amount + fee), "id": request.account_id},
        )

        await db.execute(
            text("UPDATE transactions SET status = :status, completed_at = :now WHERE id = :id"),
            {"status": TransactionStatus.COMPLETED.value, "now": datetime.utcnow(), "id": transaction.id},
        )

        await db.commit()

        transactions_total.labels(type="bill_payment", status="completed").inc()

        return TransactionResponse(
            transaction_id=transaction.id,
            reference_number=reference,
            transaction_type="bill_payment",
            amount=float(amount),
            fee=float(fee),
            currency="ETB",
            status="completed",
            description=transaction.description,
            created_at=transaction.created_at,
            completed_at=datetime.utcnow(),
        )


# Airtime Purchase Endpoint
@app.post("/api/v1/transactions/airtime", response_model=TransactionResponse)
async def purchase_airtime(
    request: AirtimeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Purchase airtime"""
    with transaction_latency.labels(type="airtime").time():
        # Get account
        result = await db.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": request.account_id})
        account = result.fetchone()

        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        amount = Decimal(str(request.amount))

        if Decimal(str(account.available_balance)) < amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")

        reference = ReferenceGenerator.generate("AIR")

        # Create transaction
        transaction = Transaction(
            reference_number=reference,
            transaction_type=TransactionType.AIRTIME.value,
            source_account_id=request.account_id,
            amount=amount,
            description=f"Airtime to {request.phone_number} ({request.operator})",
            metadata=f'{{"phone": "{request.phone_number}", "operator": "{request.operator}"}}',
            status=TransactionStatus.PROCESSING.value,
        )

        db.add(transaction)
        await db.commit()

        # Debit account
        await db.execute(
            text(
                """UPDATE accounts 
                   SET balance = balance - :amount,
                       available_balance = available_balance - :amount
                   WHERE id = :id"""
            ),
            {"amount": float(amount), "id": request.account_id},
        )

        await db.execute(
            text("UPDATE transactions SET status = :status, completed_at = :now WHERE id = :id"),
            {"status": TransactionStatus.COMPLETED.value, "now": datetime.utcnow(), "id": transaction.id},
        )

        await db.commit()

        transactions_total.labels(type="airtime", status="completed").inc()

        return TransactionResponse(
            transaction_id=transaction.id,
            reference_number=reference,
            transaction_type="airtime",
            amount=float(amount),
            fee=0,
            currency="ETB",
            status="completed",
            description=transaction.description,
            created_at=transaction.created_at,
            completed_at=datetime.utcnow(),
        )


# Transaction History
@app.get("/api/v1/transactions/{account_id}/history")
async def get_transaction_history(
    account_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction history for an account"""
    # Build query
    query = """
        SELECT * FROM transactions 
        WHERE (source_account_id = :aid OR destination_account_id = :aid)
    """
    params = {"aid": account_id}

    if start_date:
        query += " AND created_at >= :start"
        params["start"] = start_date

    if end_date:
        query += " AND created_at <= :end"
        params["end"] = end_date

    if transaction_type:
        query += " AND transaction_type = :type"
        params["type"] = transaction_type

    # Count total
    count_result = await db.execute(
        text(query.replace("SELECT *", "SELECT COUNT(*)")), params
    )
    total = count_result.scalar()

    # Get paginated results
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size

    result = await db.execute(text(query), params)
    transactions = result.fetchall()

    return {
        "transactions": [
            {
                "transaction_id": txn.id,
                "reference_number": txn.reference_number,
                "transaction_type": txn.transaction_type,
                "amount": float(txn.amount),
                "fee": float(txn.fee) if txn.fee else 0,
                "currency": txn.currency,
                "status": txn.status,
                "description": txn.description,
                "is_debit": txn.source_account_id == account_id,
                "created_at": txn.created_at.isoformat(),
                "completed_at": txn.completed_at.isoformat() if txn.completed_at else None,
            }
            for txn in transactions
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


# Transaction Details
@app.get("/api/v1/transactions/{transaction_id}")
async def get_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    """Get transaction details"""
    result = await db.execute(
        text("SELECT * FROM transactions WHERE id = :id OR reference_number = :id"),
        {"id": transaction_id},
    )
    txn = result.fetchone()

    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    return {
        "transaction_id": txn.id,
        "reference_number": txn.reference_number,
        "transaction_type": txn.transaction_type,
        "source_account_id": txn.source_account_id,
        "destination_account_id": txn.destination_account_id,
        "amount": float(txn.amount),
        "fee": float(txn.fee) if txn.fee else 0,
        "currency": txn.currency,
        "status": txn.status,
        "description": txn.description,
        "channel": txn.channel,
        "error_message": txn.error_message,
        "created_at": txn.created_at.isoformat(),
        "completed_at": txn.completed_at.isoformat() if txn.completed_at else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
