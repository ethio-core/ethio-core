"""
Ethio-Core MVP API — single service matching m7-frontend `services/api.ts` contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any, Generator, Optional

import bcrypt
import jwt
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/mvp.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev_jwt_secret_change_in_production")
JWT_ALG = "HS256"
ACCESS_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "1440"))
REFRESH_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "14"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

security_bearer = HTTPBearer(auto_error=False)


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False

_dynamic_cvv: dict[str, tuple[str, datetime]] = {}

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fayda_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone_number: Mapped[str] = mapped_column(String(40))
    date_of_birth: Mapped[str] = mapped_column(String(32))
    kyc_status: Mapped[str] = mapped_column(String(32), default="pending")
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    kyc_sessions: Mapped[list["KycSession"]] = relationship(back_populates="customer")
    documents: Mapped[list["Document"]] = relationship(back_populates="customer")
    cards: Mapped[list["Card"]] = relationship(back_populates="customer")


class KycSession(Base):
    __tablename__ = "kyc_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="in_progress")
    steps_completed_json: Mapped[str] = mapped_column(Text, default="[]")
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    customer: Mapped["Customer"] = relationship(back_populates="kyc_sessions")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="received")
    filename: Mapped[str] = mapped_column(String(512))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    customer: Mapped["Customer"] = relationship(back_populates="documents")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), index=True)
    card_number_masked: Mapped[str] = mapped_column(String(32))
    last4: Mapped[str] = mapped_column(String(4))
    card_type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    expiry_date: Mapped[str] = mapped_column(String(8))
    pin_set: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    customer: Mapped["Customer"] = relationship(back_populates="cards")


class TransactionRow(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), index=True)
    to_customer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    card_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    type: Mapped[str] = mapped_column(String(16))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="ETB")
    status: Mapped[str] = mapped_column(String(16), default="completed")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64))
    user_email: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    ip_address: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    record_hash: Mapped[str] = mapped_column(String(128))


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    os.makedirs(os.path.dirname(DATABASE_URL.replace("sqlite:///", "")) or ".", exist_ok=True)
    if DATABASE_URL.startswith("sqlite"):
        path = DATABASE_URL.replace("sqlite:///", "")
        if path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


# -----------------------------------------------------------------------------
# Seed
# -----------------------------------------------------------------------------

DEMO_CUSTOMERS = [
    ("Abebe", "Kebede", "abebe.kebede@email.com", "+251911234567", "verified", "low", "FYD-001234", "1990-05-12"),
    ("Tigist", "Haile", "tigist.haile@email.com", "+251922345678", "in_progress", "medium", "FYD-001235", "1992-08-22"),
    ("Dawit", "Mengistu", "dawit.m@email.com", "+251933456789", "pending", "low", None, "1988-12-01"),
    ("Sara", "Tesfaye", "sara.tesfaye@email.com", "+251944567890", "verified", "low", "FYD-001236", "1995-03-15"),
    ("Yonas", "Alemu", "yonas.alemu@email.com", "+251955678901", "rejected", "high", "FYD-001237", "1987-11-30"),
]


def seed_if_empty() -> None:
    with get_session() as db:
        if db.scalars(select(User).limit(1)).first():
            return

        for email, password, name, role in [
            ("admin@ethio-core.com", "admin123", "Admin User", "admin"),
            ("operator@ethio-core.com", "operator123", "Operator", "operator"),
        ]:
            db.add(
                User(
                    id=str(uuid.uuid4()),
                    email=email,
                    password_hash=_hash_password(password),
                    name=name,
                    role=role,
                )
            )

        db.flush()
        admin_user = db.scalars(select(User).where(User.email == "admin@ethio-core.com")).one()

        for fn, ln, em, ph, kyc, risk, fayda, dob in DEMO_CUSTOMERS:
            cid = str(uuid.uuid4())
            db.add(
                Customer(
                    id=cid,
                    fayda_id=fayda,
                    first_name=fn,
                    last_name=ln,
                    email=em,
                    phone_number=ph,
                    date_of_birth=dob,
                    kyc_status=kyc,
                    risk_level=risk,
                )
            )

            steps = {
                "pending": ["document_upload"],
                "in_progress": ["document_upload", "ocr_verification"],
                "verified": ["document_upload", "ocr_verification", "fayda_check", "biometric"],
                "rejected": ["document_upload", "ocr_verification"],
            }.get(kyc, [])
            db.add(
                KycSession(
                    id=str(uuid.uuid4()),
                    customer_id=cid,
                    status="verified" if kyc == "verified" else ("rejected" if kyc == "rejected" else kyc),
                    steps_completed_json=json.dumps(steps),
                    risk_score=15 if kyc == "verified" else (85 if kyc == "rejected" else None),
                )
            )

        db.flush()
        customers = list(db.scalars(select(Customer)).all())
        for i, c in enumerate(customers):
            st = ["pending", "active", "active", "blocked", "expired"][i % 5]
            ctype = "virtual" if i % 2 == 0 else "physical"
            last4 = f"{1000 + i}"
            db.add(
                Card(
                    id=str(uuid.uuid4()),
                    customer_id=c.id,
                    card_number_masked=f"4532********{last4}",
                    last4=last4,
                    card_type=ctype,
                    status=st,
                    expiry_date="12/27" if st != "expired" else "01/24",
                )
            )

        # Demo transactions
        if len(customers) >= 2:
            a, b = customers[0], customers[1]
            now = datetime.now(timezone.utc)
            rows = [
                TransactionRow(
                    id=str(uuid.uuid4()),
                    customer_id=a.id,
                    type="credit",
                    amount=15000,
                    currency="ETB",
                    status="completed",
                    description="Salary deposit",
                    created_at=now,
                ),
                TransactionRow(
                    id=str(uuid.uuid4()),
                    customer_id=b.id,
                    type="debit",
                    amount=2500,
                    currency="ETB",
                    status="completed",
                    description="POS Purchase - Shoa Supermarket",
                    created_at=now,
                ),
                TransactionRow(
                    id=str(uuid.uuid4()),
                    customer_id=customers[2].id,
                    to_customer_id=customers[3].id,
                    type="transfer",
                    amount=5000,
                    currency="ETB",
                    status="pending",
                    description=f"Transfer to {customers[3].first_name} {customers[3].last_name}",
                    created_at=now,
                ),
            ]
            for r in rows:
                db.add(r)

        for sev, typ, msg, uid, res in [
            ("high", "Failed Login Attempts", "Multiple failed login attempts detected", customers[0].id, False),
            ("critical", "Suspicious Transaction", "Large transaction amount flagged: ETB 500,000", customers[1].id, False),
            ("medium", "New Device Login", "Login from new device detected", customers[1].id, True),
            ("high", "IP Blacklist Match", "Access attempt from blacklisted IP", None, False),
            ("low", "Rate Limit Exceeded", "API rate limit exceeded for /api/v1/transactions", None, True),
        ]:
            db.add(SecurityAlert(id=str(uuid.uuid4()), type=typ, severity=sev, message=msg, user_id=uid, resolved=res))

        chain_prev = "genesis"
        for action, rt, rid, detail in [
            ("USER_LOGIN", "session", str(uuid.uuid4()), {"user_agent": "Chrome/120"}),
            ("CUSTOMER_CREATED", "customer", customers[0].id, {"customer_name": f"{customers[0].first_name} {customers[0].last_name}"}),
            ("CARD_ISSUED", "card", "seed", {"customer_id": customers[0].id}),
        ]:
            ts = datetime.now(timezone.utc)
            payload = f"{chain_prev}|{ts.isoformat()}|{action}|{rid}|{json.dumps(detail, sort_keys=True)}"
            h = hashlib.sha256(payload.encode()).hexdigest()
            db.add(
                AuditLog(
                    id=str(uuid.uuid4()),
                    user_id=admin_user.id,
                    user_email=admin_user.email,
                    action=action,
                    resource_type=rt,
                    resource_id=rid,
                    details_json=json.dumps(detail),
                    ip_address="127.0.0.1",
                    timestamp=ts,
                    record_hash=h,
                )
            )
            chain_prev = h


# -----------------------------------------------------------------------------
# App lifecycle
# -----------------------------------------------------------------------------

app = FastAPI(title="Ethio-Core MVP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    seed_if_empty()


# -----------------------------------------------------------------------------
# Auth helpers
# -----------------------------------------------------------------------------

def _access_token(user: User) -> str:
    exp = int(time.time()) + ACCESS_MINUTES * 60
    return jwt.encode(
        {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "typ": "access",
            "exp": exp,
        },
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def _refresh_token_jwt(user: User) -> str:
    exp = int(time.time()) + REFRESH_DAYS * 86400
    return jwt.encode(
        {"sub": user.id, "typ": "refresh", "exp": exp},
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def _decode_token(token: str, expected_typ: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("typ") != expected_typ:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_bearer)],
) -> dict[str, Any]:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _decode_token(creds.credentials, "access")


def optional_client_ip(request: Request) -> str:
    return request.client.host if request.client else "0.0.0.0"


def write_audit(
    db: Session,
    user: dict[str, Any],
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict[str, Any],
    ip: str,
) -> None:
    last = db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1)).first()
    chain_prev = last.record_hash if last else "genesis"
    ts = datetime.now(timezone.utc)
    payload = f"{chain_prev}|{ts.isoformat()}|{action}|{resource_id}|{json.dumps(details, sort_keys=True)}"
    h = hashlib.sha256(payload.encode()).hexdigest()
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            user_id=user.get("sub", "system"),
            user_email=user.get("email", "system@ethio-core.com"),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=json.dumps(details),
            ip_address=ip,
            timestamp=ts,
            record_hash=h,
        )
    )


# -----------------------------------------------------------------------------
# Pydantic DTOs
# -----------------------------------------------------------------------------


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    date_of_birth: str


class BlockCardBody(BaseModel):
    reason: str = "blocked"


class PinBody(BaseModel):
    pin: str = Field(min_length=4, max_length=12)


class TransferBody(BaseModel):
    from_customer_id: str
    to_customer_id: str
    amount: float = Field(gt=0)
    currency: str = "ETB"
    description: Optional[str] = None


class ReverseBody(BaseModel):
    reason: str = "reversal"


class BiometricFaceBody(BaseModel):
    customer_id: str
    image_data: str


class LivenessBody(BaseModel):
    image_data: str


# -----------------------------------------------------------------------------
# Routes: health & auth
# -----------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "mvp-api"}


@app.post("/api/v1/auth/login")
def login(body: LoginBody, request: Request) -> dict[str, str]:
    with get_session() as db:
        user = db.execute(select(User).where(User.email == str(body.email))).scalar_one_or_none()
        if not user or not _verify_password(body.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        access = _access_token(user)
        refresh = _refresh_token_jwt(user)
        write_audit(
            db,
            {"sub": user.id, "email": user.email},
            "USER_LOGIN",
            "session",
            str(uuid.uuid4()),
            {"ip": optional_client_ip(request)},
            optional_client_ip(request),
        )
    return {"access_token": access, "refresh_token": refresh}


@app.get("/api/v1/auth/me")
def me(user: Annotated[dict[str, Any], Depends(get_current_user)]) -> dict[str, str]:
    return {"id": user["sub"], "email": user["email"], "name": user.get("name", ""), "role": user.get("role", "admin")}


@app.post("/api/v1/auth/logout")
def logout(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, str]:
    with get_session() as db:
        write_audit(
            db,
            user,
            "USER_LOGOUT",
            "session",
            user["sub"],
            {},
            optional_client_ip(request),
        )
    return {"ok": True}


@app.post("/api/v1/auth/refresh")
def refresh(body: RefreshBody) -> dict[str, str]:
    payload = _decode_token(body.refresh_token, "refresh")
    with get_session() as db:
        user = db.execute(select(User).where(User.id == payload["sub"])).scalar_one_or_none()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found")
        access = _access_token(user)
    return {"access_token": access}


# -----------------------------------------------------------------------------
# Identity
# -----------------------------------------------------------------------------


def _customer_out(c: Customer) -> dict[str, Any]:
    return {
        "id": c.id,
        "fayda_id": c.fayda_id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "email": c.email,
        "phone_number": c.phone_number,
        "date_of_birth": c.date_of_birth,
        "kyc_status": c.kyc_status,
        "risk_level": c.risk_level,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


@app.get("/api/v1/identity/customers")
def list_customers(
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
) -> dict[str, Any]:
    page = max(page, 1)
    limit = min(max(limit, 1), 200)
    offset = (page - 1) * limit
    with get_session() as db:
        cq = select(func.count()).select_from(Customer)
        if status:
            cq = cq.where(Customer.kyc_status == status)
        total = int(db.scalar(cq) or 0)
        q = select(Customer).order_by(Customer.created_at.desc()).offset(offset).limit(limit)
        if status:
            q = select(Customer).where(Customer.kyc_status == status).order_by(Customer.created_at.desc()).offset(offset).limit(limit)
        rows = db.scalars(q).all()
        return {"items": [_customer_out(c) for c in rows], "total": total}


@app.get("/api/v1/identity/customers/{customer_id}")
def get_customer(
    customer_id: str,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    with get_session() as db:
        c = db.get(Customer, customer_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer not found")
        return _customer_out(c)


@app.post("/api/v1/identity/customers", status_code=201)
def create_customer(
    body: CustomerCreate,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, Any]:
    with get_session() as db:
        exists = db.scalars(select(Customer).where(Customer.email == str(body.email))).first()
        if exists:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        c = Customer(
            id=str(uuid.uuid4()),
            first_name=body.first_name,
            last_name=body.last_name,
            email=str(body.email),
            phone_number=body.phone_number,
            date_of_birth=body.date_of_birth,
            kyc_status="pending",
            risk_level="low",
        )
        db.add(c)
        db.add(
            KycSession(
                id=str(uuid.uuid4()),
                customer_id=c.id,
                status="pending",
                steps_completed_json=json.dumps(["document_upload"]),
                risk_score=None,
            )
        )
        db.flush()
        write_audit(
            db,
            user,
            "CUSTOMER_CREATED",
            "customer",
            c.id,
            {"email": c.email, "name": f"{c.first_name} {c.last_name}"},
            optional_client_ip(request),
        )
        return _customer_out(c)


@app.post("/api/v1/identity/customers/{customer_id}/kyc")
def initiate_kyc(
    customer_id: str,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, Any]:
    with get_session() as db:
        c = db.get(Customer, customer_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer not found")
        sess = KycSession(
            id=str(uuid.uuid4()),
            customer_id=c.id,
            status="in_progress",
            steps_completed_json=json.dumps(["document_upload"]),
        )
        db.add(sess)
        c.kyc_status = "in_progress"
        db.flush()
        write_audit(db, user, "KYC_INITIATED", "kyc", sess.id, {"customer_id": c.id}, optional_client_ip(request))
        return {
            "id": sess.id,
            "customer_id": c.id,
            "status": sess.status,
            "steps_completed": json.loads(sess.steps_completed_json),
            "created_at": sess.created_at.isoformat(),
        }


@app.get("/api/v1/identity/kyc/sessions")
def list_kyc_sessions(
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    """Dashboard KYC table: join customer + session."""
    with get_session() as db:
        sessions = db.scalars(select(KycSession).order_by(KycSession.created_at.desc())).all()
        out = []
        for s in sessions:
            cust = db.get(Customer, s.customer_id)
            if not cust:
                continue
            out.append(
                {
                    "id": s.id,
                    "customer_name": f"{cust.first_name} {cust.last_name}",
                    "email": cust.email,
                    "status": s.status,
                    "steps_completed": json.loads(s.steps_completed_json),
                    "risk_score": s.risk_score,
                    "submitted_at": s.created_at.isoformat(),
                    "verified_at": s.created_at.isoformat() if s.status == "verified" else None,
                }
            )
        return {"items": out}


@app.post("/api/v1/identity/customers/{customer_id}/documents")
async def upload_document(
    customer_id: str,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Form("national_id"),
) -> dict[str, Any]:
    with get_session() as db:
        c = db.get(Customer, customer_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer not found")
        fname = file.filename or "upload"
        safe = "".join(ch for ch in fname if ch.isalnum() or ch in "._-")[:200]
        uid = str(uuid.uuid4())
        path = os.path.join(UPLOAD_DIR, f"{uid}_{safe}")
        content = await file.read()
        with open(path, "wb") as f:
            f.write(content)
        doc = Document(
            id=str(uuid.uuid4()),
            customer_id=c.id,
            document_type=document_type,
            status="received",
            filename=path,
        )
        db.add(doc)
        write_audit(
            db,
            user,
            "DOCUMENT_UPLOADED",
            "document",
            doc.id,
            {"customer_id": c.id, "document_type": document_type},
            optional_client_ip(request),
        )
        return {
            "id": doc.id,
            "customer_id": c.id,
            "document_type": doc.document_type,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat(),
        }


# -----------------------------------------------------------------------------
# Biometric (stub)
# -----------------------------------------------------------------------------


@app.post("/api/v1/biometric/face/enroll")
def bio_enroll(
    body: BiometricFaceBody,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    if len(body.image_data) < 32:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid image_data")
    return {
        "id": str(uuid.uuid4()),
        "customer_id": body.customer_id,
        "status": "enrolled",
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/biometric/face/verify")
def bio_verify(
    body: BiometricFaceBody,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    ok = len(body.image_data) >= 32
    return {"verified": ok, "confidence": 0.92 if ok else 0.2, "message": "Match" if ok else "No match"}


@app.post("/api/v1/biometric/liveness")
def bio_liveness(
    body: LivenessBody,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    live = len(body.image_data) >= 64
    return {
        "is_live": live,
        "confidence": 0.88 if live else 0.35,
        "checks_passed": ["texture", "depth"] if live else ["texture"],
    }


# -----------------------------------------------------------------------------
# Cards
# -----------------------------------------------------------------------------


def _card_out(card: Card, db: Session) -> dict[str, Any]:
    cust = db.get(Customer, card.customer_id)
    name = f"{cust.first_name} {cust.last_name}" if cust else ""
    return {
        "id": card.id,
        "customer_id": card.customer_id,
        "customer_name": name,
        "card_number_masked": card.card_number_masked,
        "card_type": card.card_type,
        "status": card.status,
        "expiry_date": card.expiry_date,
        "created_at": card.created_at.isoformat(),
    }


@app.get("/api/v1/card/cards")
def list_cards(
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    customer_id: Optional[str] = None,
    page: int = 1,
    limit: int = 100,
) -> dict[str, Any]:
    page = max(page, 1)
    limit = min(max(limit, 1), 500)
    offset = (page - 1) * limit
    with get_session() as db:
        q = select(Card)
        if customer_id:
            q = q.where(Card.customer_id == customer_id)
        cq = select(func.count()).select_from(Card)
        if customer_id:
            cq = cq.where(Card.customer_id == customer_id)
        total = int(db.scalar(cq) or 0)
        rows = db.scalars(q.order_by(Card.created_at.desc()).offset(offset).limit(limit)).all()
        return {"items": [_card_out(c, db) for c in rows], "total": total}


@app.get("/api/v1/card/cards/{card_id}")
def get_card(
    card_id: str,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    with get_session() as db:
        card = db.get(Card, card_id)
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found")
        d = _card_out(card, db)
        del d["customer_name"]
        return d


class RequestCardBody(BaseModel):
    customer_id: str
    card_type: str = "virtual"


@app.post("/api/v1/card/cards", status_code=201)
def request_card(
    body: RequestCardBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, Any]:
    if body.card_type not in ("virtual", "physical"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid card_type")
    with get_session() as db:
        c = db.get(Customer, body.customer_id)
        if not c:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer not found")
        last4 = f"{secrets.randbelow(9000) + 1000}"
        card = Card(
            id=str(uuid.uuid4()),
            customer_id=c.id,
            card_number_masked=f"4532********{last4}",
            last4=last4,
            card_type=body.card_type,
            status="pending",
            expiry_date="12/28",
        )
        db.add(card)
        db.flush()
        write_audit(
            db,
            user,
            "CARD_ISSUED",
            "card",
            card.id,
            {"customer_id": c.id, "card_type": body.card_type},
            optional_client_ip(request),
        )
        d = _card_out(card, db)
        del d["customer_name"]
        return d


@app.post("/api/v1/card/cards/{card_id}/activate")
def activate_card(
    card_id: str,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, Any]:
    with get_session() as db:
        card = db.get(Card, card_id)
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found")
        card.status = "active"
        write_audit(db, user, "CARD_ACTIVATED", "card", card.id, {}, optional_client_ip(request))
        d = _card_out(card, db)
        del d["customer_name"]
        return d


@app.post("/api/v1/card/cards/{card_id}/block")
def block_card(
    card_id: str,
    body: BlockCardBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, Any]:
    with get_session() as db:
        card = db.get(Card, card_id)
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found")
        card.status = "blocked"
        write_audit(
            db,
            user,
            "CARD_BLOCKED",
            "card",
            card.id,
            {"reason": body.reason},
            optional_client_ip(request),
        )
        d = _card_out(card, db)
        del d["customer_name"]
        return d


@app.post("/api/v1/card/cards/{card_id}/pin")
def set_pin(
    card_id: str,
    body: PinBody,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, str]:
    with get_session() as db:
        card = db.get(Card, card_id)
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found")
        card.pin_set = True
    return {"ok": True}


@app.get("/api/v1/card/cards/{card_id}/dynamic-cvv")
def dynamic_cvv(
    card_id: str,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, str]:
    with get_session() as db:
        card = db.get(Card, card_id)
        if not card:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Card not found")
    cvv = f"{secrets.randbelow(900) + 100}"
    exp = datetime.now(timezone.utc) + timedelta(minutes=5)
    _dynamic_cvv[card_id] = (cvv, exp)
    return {"cvv": cvv, "expires_at": exp.isoformat()}


# -----------------------------------------------------------------------------
# Transactions
# -----------------------------------------------------------------------------


def _txn_out(t: TransactionRow, db: Session) -> dict[str, Any]:
    cust = db.get(Customer, t.customer_id)
    name = f"{cust.first_name} {cust.last_name}" if cust else t.customer_id
    return {
        "id": t.id,
        "customer_id": t.customer_id,
        "customer_name": name,
        "card_id": t.card_id,
        "type": t.type,
        "amount": t.amount,
        "currency": t.currency,
        "status": t.status,
        "description": t.description,
        "created_at": t.created_at.isoformat(),
    }


@app.get("/api/v1/transaction/transactions")
def list_transactions(
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    page: int = 1,
    limit: int = 50,
    customer_id: Optional[str] = None,
    card_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> dict[str, Any]:
    page = max(page, 1)
    limit = min(max(limit, 1), 200)
    offset = (page - 1) * limit
    with get_session() as db:
        q = select(TransactionRow)
        if customer_id:
            q = q.where(TransactionRow.customer_id == customer_id)
        if card_id:
            q = q.where(TransactionRow.card_id == card_id)
        if status:
            q = q.where(TransactionRow.status == status)
        if from_date:
            q = q.where(TransactionRow.created_at >= datetime.fromisoformat(from_date.replace("Z", "+00:00")))
        if to_date:
            q = q.where(TransactionRow.created_at <= datetime.fromisoformat(to_date.replace("Z", "+00:00")))
        cq = select(func.count()).select_from(TransactionRow)
        if customer_id:
            cq = cq.where(TransactionRow.customer_id == customer_id)
        if card_id:
            cq = cq.where(TransactionRow.card_id == card_id)
        if status:
            cq = cq.where(TransactionRow.status == status)
        if from_date:
            cq = cq.where(TransactionRow.created_at >= datetime.fromisoformat(from_date.replace("Z", "+00:00")))
        if to_date:
            cq = cq.where(TransactionRow.created_at <= datetime.fromisoformat(to_date.replace("Z", "+00:00")))
        total = int(db.scalar(cq) or 0)
        rows = db.scalars(q.order_by(TransactionRow.created_at.desc()).offset(offset).limit(limit)).all()
        return {"items": [_txn_out(t, db) for t in rows], "total": total}


@app.get("/api/v1/transaction/transactions/{txn_id}")
def get_transaction(
    txn_id: str,
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    with get_session() as db:
        t = db.get(TransactionRow, txn_id)
        if not t:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        d = _txn_out(t, db)
        return d


@app.post("/api/v1/transaction/transfer", status_code=201)
def transfer(
    body: TransferBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, Any]:
    with get_session() as db:
        fc = db.get(Customer, body.from_customer_id)
        tc = db.get(Customer, body.to_customer_id)
        if not fc or not tc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer not found")
        desc = body.description or f"Transfer to {tc.first_name} {tc.last_name}"
        t = TransactionRow(
            id=str(uuid.uuid4()),
            customer_id=fc.id,
            to_customer_id=tc.id,
            type="transfer",
            amount=float(body.amount),
            currency=body.currency,
            status="completed",
            description=desc,
        )
        db.add(t)
        db.flush()
        write_audit(
            db,
            user,
            "TRANSACTION_TRANSFER",
            "transaction",
            t.id,
            {"from": fc.id, "to": tc.id, "amount": body.amount},
            optional_client_ip(request),
        )
        return {
            "id": t.id,
            "customer_id": t.customer_id,
            "card_id": t.card_id,
            "type": t.type,
            "amount": t.amount,
            "currency": t.currency,
            "status": t.status,
            "description": t.description,
            "created_at": t.created_at.isoformat(),
        }


@app.post("/api/v1/transaction/transactions/{txn_id}/reverse")
def reverse_txn(
    txn_id: str,
    body: ReverseBody,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, Any]:
    with get_session() as db:
        t = db.get(TransactionRow, txn_id)
        if not t:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        t.status = "reversed"
        t.description = f"{t.description} (reversed: {body.reason})"
        db.flush()
        write_audit(
            db,
            user,
            "TRANSACTION_REVERSED",
            "transaction",
            t.id,
            {"reason": body.reason},
            optional_client_ip(request),
        )
        return {
            "id": t.id,
            "customer_id": t.customer_id,
            "card_id": t.card_id,
            "type": t.type,
            "amount": t.amount,
            "currency": t.currency,
            "status": t.status,
            "description": t.description,
            "created_at": t.created_at.isoformat(),
        }


# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------


@app.get("/api/v1/security/audit-logs")
def audit_logs(
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    page: int = 1,
    limit: int = 50,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    page = max(page, 1)
    limit = min(max(limit, 1), 200)
    offset = (page - 1) * limit
    with get_session() as db:
        q = select(AuditLog)
        if user_id:
            q = q.where(AuditLog.user_id == user_id)
        cq = select(func.count()).select_from(AuditLog)
        if user_id:
            cq = cq.where(AuditLog.user_id == user_id)
        total = int(db.scalar(cq) or 0)
        rows = db.scalars(q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)).all()
        items = []
        for r in rows:
            items.append(
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "user_email": r.user_email,
                    "action": r.action,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "details": json.loads(r.details_json or "{}"),
                    "ip_address": r.ip_address,
                    "timestamp": r.timestamp.isoformat(),
                    "hash": r.record_hash[:16] + "...",
                }
            )
        return {"items": items, "total": total}


@app.get("/api/v1/security/alerts")
def security_alerts(
    _: Annotated[dict[str, Any], Depends(get_current_user)],
    page: int = 1,
    limit: int = 50,
    severity: Optional[str] = None,
) -> dict[str, Any]:
    page = max(page, 1)
    limit = min(max(limit, 1), 200)
    offset = (page - 1) * limit
    with get_session() as db:
        q = select(SecurityAlert)
        if severity:
            q = q.where(SecurityAlert.severity == severity)
        cq = select(func.count()).select_from(SecurityAlert)
        if severity:
            cq = cq.where(SecurityAlert.severity == severity)
        total = int(db.scalar(cq) or 0)
        rows = db.scalars(q.order_by(SecurityAlert.created_at.desc()).offset(offset).limit(limit)).all()
        return {
            "items": [
                {
                    "id": r.id,
                    "type": r.type,
                    "severity": r.severity,
                    "message": r.message,
                    "user_id": r.user_id,
                    "resolved": r.resolved,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
            "total": total,
        }


@app.post("/api/v1/security/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    request: Request,
) -> dict[str, str]:
    with get_session() as db:
        a = db.get(SecurityAlert, alert_id)
        if not a:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
        a.resolved = True
        write_audit(db, user, "SECURITY_ALERT_RESOLVED", "alert", a.id, {}, optional_client_ip(request))
    return {"ok": True}


@app.get("/api/v1/security/integrity/verify")
def integrity(
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    with get_session() as db:
        rows = db.scalars(select(AuditLog).order_by(AuditLog.timestamp.asc())).all()
        chain_prev = "genesis"
        invalid: list[str] = []
        for r in rows:
            detail = json.loads(r.details_json or "{}")
            payload = f"{chain_prev}|{r.timestamp.isoformat()}|{r.action}|{r.resource_id}|{json.dumps(detail, sort_keys=True)}"
            h = hashlib.sha256(payload.encode()).hexdigest()
            if h != r.record_hash:
                invalid.append(r.id)
            chain_prev = r.record_hash
        return {
            "status": "valid" if not invalid else "invalid",
            "records_checked": len(rows),
            "invalid_records": invalid,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------


@app.get("/api/v1/stats/dashboard")
def dashboard_stats(
    _: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    today = date.today()
    with get_session() as db:
        total_customers = int(db.scalar(select(func.count()).select_from(Customer)) or 0)
        active_cards = int(db.scalar(select(func.count()).select_from(Card).where(Card.status == "active")) or 0)
        pending_kyc = int(
            db.scalar(
                select(func.count())
                .select_from(Customer)
                .where(Customer.kyc_status.in_(("pending", "in_progress")))
            )
            or 0
        )
        security_alerts_n = int(
            db.scalar(select(func.count()).select_from(SecurityAlert).where(SecurityAlert.resolved.is_(False))) or 0
        )
        txn_today = db.scalars(
            select(TransactionRow).where(func.date(TransactionRow.created_at) == today)
        ).all()
        transactions_today = len(txn_today)
        volume_today = sum(t.amount for t in txn_today if t.status == "completed")

        recent_tx = db.scalars(select(TransactionRow).order_by(TransactionRow.created_at.desc()).limit(8)).all()
        activities = []
        for t in recent_tx:
            cust = db.get(Customer, t.customer_id)
            cname = f"{cust.first_name} {cust.last_name}" if cust else ""
            activities.append(
                {
                    "id": t.id,
                    "type": {"transfer": "Transfer", "credit": "Credit", "debit": "Debit"}.get(t.type, t.type.title()),
                    "description": t.description or f"{t.type} — {cname}".strip(" —"),
                    "status": t.status,
                    "timestamp": t.created_at.isoformat(),
                }
            )

        # simple week chart: last 7 days count
        chart_tx = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            cnt = int(
                db.scalar(
                    select(func.count())
                    .select_from(TransactionRow)
                    .where(func.date(TransactionRow.created_at) == d)
                )
                or 0
            )
            chart_tx.append({"name": d.strftime("%a"), "transactions": cnt})

        vol_months = []
        for m in range(6):
            vol_months.append({"name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"][m], "volume": float(4_500_000 + m * 400_000)})

    return {
        "total_customers": total_customers,
        "active_cards": active_cards,
        "transactions_today": transactions_today,
        "transaction_volume_today": float(volume_today),
        "pending_kyc": pending_kyc,
        "security_alerts": security_alerts_n,
        "growth_rates": {"customers": 5.0, "transactions": 3.0},
        "chart_transactions_week": chart_tx,
        "chart_volume_months": vol_months,
        "recent_activity": activities,
    }
