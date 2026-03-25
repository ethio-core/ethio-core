"""
M6 SSO Service - OAuth2/OIDC & Role-Based Access Control
Ethiopian Banking Core Platform
"""

import hashlib
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import aiohttp
from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.responses import Response

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/sso_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/5")
EVENT_STORE_URL = os.getenv("EVENT_STORE_URL", "http://event-store:8000")

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# OAuth2 Configuration
OAUTH2_ISSUER = os.getenv("OAUTH2_ISSUER", "https://auth.ethio-bank.et")
OAUTH2_AUTHORIZATION_ENDPOINT = f"{OAUTH2_ISSUER}/authorize"
OAUTH2_TOKEN_ENDPOINT = f"{OAUTH2_ISSUER}/token"

# Metrics
auth_attempts = Counter("sso_auth_attempts_total", "Authentication attempts", ["method", "status"])
token_operations = Counter("sso_token_operations_total", "Token operations", ["operation"])
session_count = Counter("sso_sessions_total", "Total sessions created")
auth_latency = Histogram("sso_auth_latency_seconds", "Authentication latency")

# Database setup
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20, max_overflow=30)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
security_bearer = HTTPBearer()


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING = "pending"
    SUSPENDED = "suspended"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    ID = "id"


class GrantType(str, Enum):
    PASSWORD = "password"
    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"


# Database Models
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone_number = Column(String(20), unique=True)
    password_hash = Column(String(255), nullable=False)
    customer_id = Column(String(36), index=True)  # Link to identity service
    status = Column(String(20), default=UserStatus.PENDING.value)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(100))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    last_login = Column(DateTime)
    last_password_change = Column(DateTime)
    password_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
        Index("idx_user_customer", "customer_id"),
    )


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    resource = Column(String(50), nullable=False)
    action = Column(String(20), nullable=False)  # create, read, update, delete
    created_at = Column(DateTime, default=datetime.utcnow)


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    role_id = Column(String(36), nullable=False, index=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(String(36))
    expires_at = Column(DateTime)

    __table_args__ = (Index("idx_user_role", "user_id", "role_id", unique=True),)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_id = Column(String(36), nullable=False, index=True)
    permission_id = Column(String(36), nullable=False, index=True)

    __table_args__ = (Index("idx_role_permission", "role_id", "permission_id", unique=True),)


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(100), unique=True, nullable=False)
    client_secret_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    redirect_uris = Column(Text)  # JSON array
    allowed_scopes = Column(Text)  # JSON array
    allowed_grant_types = Column(Text)  # JSON array
    is_confidential = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuthorizationCode(Base):
    __tablename__ = "authorization_codes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(100), unique=True, nullable=False)
    client_id = Column(String(100), nullable=False)
    user_id = Column(String(36), nullable=False)
    redirect_uri = Column(String(500), nullable=False)
    scope = Column(String(500))
    code_challenge = Column(String(128))  # PKCE
    code_challenge_method = Column(String(10))  # S256 or plain
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token_hash = Column(String(128), unique=True, nullable=False)
    user_id = Column(String(36), nullable=False, index=True)
    client_id = Column(String(100))
    scope = Column(String(500))
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    session_token = Column(String(128), unique=True, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True)
    action = Column(String(50), nullable=False)
    resource = Column(String(50))
    resource_id = Column(String(36))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    details = Column(Text)  # JSON
    status = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_audit_date", "created_at"),)


# Pydantic Models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    phone_number: Optional[str] = None
    password: str = Field(..., min_length=8)
    customer_id: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    phone_number: Optional[str] = None
    status: str
    email_verified: bool
    phone_verified: bool
    mfa_enabled: bool
    roles: list[str] = []
    created_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None
    device_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None


class TokenIntrospectResponse(BaseModel):
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    username: Optional[str] = None
    token_type: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    sub: Optional[str] = None


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None


class PermissionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    resource: str
    action: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


class ResetPasswordRequest(BaseModel):
    email: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_code_uri: str
    backup_codes: list[str]


# Token Service
class TokenService:
    @staticmethod
    def create_access_token(
        user_id: str,
        username: str,
        roles: list[str],
        permissions: list[str],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode = {
            "sub": user_id,
            "username": username,
            "roles": roles,
            "permissions": permissions,
            "type": TokenType.ACCESS.value,
            "iat": datetime.utcnow(),
            "exp": expire,
            "iss": OAUTH2_ISSUER,
        }

        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create refresh token"""
        return secrets.token_urlsafe(64)

    @staticmethod
    def create_id_token(
        user_id: str,
        username: str,
        email: str,
        client_id: str,
        nonce: Optional[str] = None,
    ) -> str:
        """Create OIDC ID token"""
        expire = datetime.utcnow() + timedelta(hours=1)

        to_encode = {
            "sub": user_id,
            "preferred_username": username,
            "email": email,
            "aud": client_id,
            "type": TokenType.ID.value,
            "iat": datetime.utcnow(),
            "exp": expire,
            "iss": OAUTH2_ISSUER,
        }

        if nonce:
            to_encode["nonce"] = nonce

        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )


# Password Service
class PasswordService:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, list[str]]:
        """Validate password meets security requirements"""
        errors = []

        if len(password) < 8:
            errors.append("Password must be at least 8 characters")

        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors


# MFA Service
class MFAService:
    @staticmethod
    def generate_secret() -> str:
        """Generate TOTP secret"""
        return secrets.token_hex(20)

    @staticmethod
    def generate_totp_uri(secret: str, username: str, issuer: str = "EthioBank") -> str:
        """Generate TOTP URI for QR code"""
        import base64

        encoded_secret = base64.b32encode(secret.encode()).decode()
        return f"otpauth://totp/{issuer}:{username}?secret={encoded_secret}&issuer={issuer}"

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """Verify TOTP code (simplified - use pyotp in production)"""
        import hmac
        import struct
        import time

        # Simplified TOTP verification - use proper library in production
        try:
            current_time = int(time.time()) // 30
            for time_offset in [-1, 0, 1]:
                expected = MFAService._generate_totp(secret, current_time + time_offset)
                if hmac.compare_digest(code, expected):
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def _generate_totp(secret: str, counter: int) -> str:
        """Generate TOTP code"""
        import hmac
        import struct

        key = secret.encode()
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, "sha1").digest()
        offset = h[-1] & 0x0F
        code = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
        return str(code % 1000000).zfill(6)

    @staticmethod
    def generate_backup_codes(count: int = 10) -> list[str]:
        """Generate backup codes"""
        return [secrets.token_hex(4).upper() for _ in range(count)]


# Event Publisher
class EventPublisher:
    def __init__(self, event_store_url: str):
        self.event_store_url = event_store_url

    async def publish(self, event_type: str, aggregate_id: str, data: dict):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "aggregate_type": "auth",
            "aggregate_id": aggregate_id,
            "data": data,
            "metadata": {"service": "m6-sso", "version": "1.0.0"},
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
token_service = TokenService()
password_service = PasswordService()
mfa_service = MFAService()
event_publisher = EventPublisher(EVENT_STORE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default roles
    async with async_session() as db:
        await create_default_roles(db)

    yield
    await engine.dispose()


async def create_default_roles(db: AsyncSession):
    """Create default system roles"""
    default_roles = [
        ("admin", "System Administrator", True),
        ("user", "Regular User", True),
        ("manager", "Branch Manager", True),
        ("teller", "Bank Teller", True),
        ("auditor", "System Auditor", True),
    ]

    for name, description, is_system in default_roles:
        result = await db.execute(text("SELECT id FROM roles WHERE name = :name"), {"name": name})
        if not result.fetchone():
            role = Role(name=name, description=description, is_system_role=is_system)
            db.add(role)

    await db.commit()


# FastAPI Application
app = FastAPI(
    title="M6 SSO Service",
    description="OAuth2/OIDC & Role-Based Access Control for Ethiopian Banking",
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = token_service.verify_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
    user = result.fetchone()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is not active")

    return user


# Health & Metrics
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "m6-sso", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")


# OIDC Discovery
@app.get("/.well-known/openid-configuration")
async def openid_configuration():
    """OpenID Connect Discovery"""
    return {
        "issuer": OAUTH2_ISSUER,
        "authorization_endpoint": f"{OAUTH2_ISSUER}/api/v1/oauth/authorize",
        "token_endpoint": f"{OAUTH2_ISSUER}/api/v1/oauth/token",
        "userinfo_endpoint": f"{OAUTH2_ISSUER}/api/v1/oauth/userinfo",
        "jwks_uri": f"{OAUTH2_ISSUER}/.well-known/jwks.json",
        "registration_endpoint": f"{OAUTH2_ISSUER}/api/v1/oauth/register",
        "scopes_supported": ["openid", "profile", "email", "phone", "offline_access"],
        "response_types_supported": ["code", "token", "id_token", "code token", "code id_token"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials", "password"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256", "RS256"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "code_challenge_methods_supported": ["S256", "plain"],
    }


# User Registration
@app.post("/api/v1/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user"""
    # Validate password strength
    is_valid, errors = password_service.validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": errors})

    # Check for existing user
    result = await db.execute(
        text("SELECT id FROM users WHERE username = :username OR email = :email"),
        {"username": user_data.username, "email": user_data.email},
    )
    if result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        phone_number=user_data.phone_number,
        password_hash=password_service.hash_password(user_data.password),
        customer_id=user_data.customer_id,
        password_expires_at=datetime.utcnow() + timedelta(days=90),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Assign default role
    result = await db.execute(text("SELECT id FROM roles WHERE name = 'user'"))
    role = result.fetchone()
    if role:
        user_role = UserRole(user_id=user.id, role_id=role[0])
        db.add(user_role)
        await db.commit()

    background_tasks.add_task(
        event_publisher.publish,
        "UserRegistered",
        user.id,
        {"username": user.username, "email": user.email},
    )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        status=user.status,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        mfa_enabled=user.mfa_enabled,
        roles=["user"],
        created_at=user.created_at,
    )


# Authentication
@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return tokens"""
    with auth_latency.time():
        # Find user
        result = await db.execute(
            text("SELECT * FROM users WHERE username = :username OR email = :username"),
            {"username": request.username},
        )
        user = result.fetchone()

        if not user:
            auth_attempts.labels(method="password", status="user_not_found").inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Check if locked
        if user.locked_until and datetime.utcnow() < user.locked_until:
            auth_attempts.labels(method="password", status="locked").inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked until {user.locked_until}",
            )

        # Verify password
        if not password_service.verify_password(request.password, user.password_hash):
            # Increment failed attempts
            new_attempts = user.failed_login_attempts + 1
            locked_until = None

            if new_attempts >= 5:
                locked_until = datetime.utcnow() + timedelta(hours=1)

            await db.execute(
                text(
                    "UPDATE users SET failed_login_attempts = :attempts, locked_until = :locked WHERE id = :id"
                ),
                {"attempts": new_attempts, "locked": locked_until, "id": user.id},
            )
            await db.commit()

            auth_attempts.labels(method="password", status="invalid_password").inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Check MFA
        if user.mfa_enabled:
            if not request.mfa_code:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="MFA code required",
                    headers={"X-MFA-Required": "true"},
                )

            if not mfa_service.verify_totp(user.mfa_secret, request.mfa_code):
                auth_attempts.labels(method="mfa", status="invalid_code").inc()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code",
                )

        # Check user status
        if user.status != UserStatus.ACTIVE.value:
            auth_attempts.labels(method="password", status="inactive").inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user.status}",
            )

        # Get user roles and permissions
        roles_result = await db.execute(
            text(
                """SELECT r.name FROM roles r 
                   JOIN user_roles ur ON r.id = ur.role_id 
                   WHERE ur.user_id = :uid"""
            ),
            {"uid": user.id},
        )
        roles = [r[0] for r in roles_result.fetchall()]

        permissions_result = await db.execute(
            text(
                """SELECT DISTINCT p.name FROM permissions p
                   JOIN role_permissions rp ON p.id = rp.permission_id
                   JOIN user_roles ur ON rp.role_id = ur.role_id
                   WHERE ur.user_id = :uid"""
            ),
            {"uid": user.id},
        )
        permissions = [p[0] for p in permissions_result.fetchall()]

        # Generate tokens
        access_token = token_service.create_access_token(
            user.id, user.username, roles, permissions
        )
        refresh_token = token_service.create_refresh_token(user.id)

        # Store refresh token
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        refresh_record = RefreshToken(
            token_hash=refresh_token_hash,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(refresh_record)

        # Create session
        session_token = secrets.token_urlsafe(32)
        session = Session(
            user_id=user.id,
            session_token=session_token,
            ip_address=req.client.host if req.client else None,
            user_agent=req.headers.get("user-agent"),
            device_id=request.device_id,
            expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(session)

        # Update user
        await db.execute(
            text(
                "UPDATE users SET failed_login_attempts = 0, locked_until = NULL, last_login = :now WHERE id = :id"
            ),
            {"now": datetime.utcnow(), "id": user.id},
        )

        # Audit log
        audit = AuditLog(
            user_id=user.id,
            action="login",
            ip_address=req.client.host if req.client else None,
            user_agent=req.headers.get("user-agent"),
            status="success",
        )
        db.add(audit)

        await db.commit()

        auth_attempts.labels(method="password", status="success").inc()
        session_count.inc()
        token_operations.labels(operation="access_token_created").inc()
        token_operations.labels(operation="refresh_token_created").inc()

        background_tasks.add_task(
            event_publisher.publish,
            "UserLoggedIn",
            user.id,
            {"username": user.username, "ip": req.client.host if req.client else None},
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
        )


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_tokens(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token"""
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    result = await db.execute(
        text(
            """SELECT rt.*, u.username, u.status FROM refresh_tokens rt
               JOIN users u ON rt.user_id = u.id
               WHERE rt.token_hash = :hash"""
        ),
        {"hash": token_hash},
    )
    record = result.fetchone()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if record.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    if datetime.utcnow() > record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    if record.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    # Get roles and permissions
    roles_result = await db.execute(
        text(
            """SELECT r.name FROM roles r 
               JOIN user_roles ur ON r.id = ur.role_id 
               WHERE ur.user_id = :uid"""
        ),
        {"uid": record.user_id},
    )
    roles = [r[0] for r in roles_result.fetchall()]

    permissions_result = await db.execute(
        text(
            """SELECT DISTINCT p.name FROM permissions p
               JOIN role_permissions rp ON p.id = rp.permission_id
               JOIN user_roles ur ON rp.role_id = ur.role_id
               WHERE ur.user_id = :uid"""
        ),
        {"uid": record.user_id},
    )
    permissions = [p[0] for p in permissions_result.fetchall()]

    # Generate new access token
    access_token = token_service.create_access_token(
        record.user_id, record.username, roles, permissions
    )

    token_operations.labels(operation="access_token_refreshed").inc()

    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post("/api/v1/auth/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
):
    """Logout user and invalidate tokens"""
    token = credentials.credentials
    payload = token_service.verify_token(token)

    user_id = payload.get("sub")

    # Revoke all refresh tokens
    await db.execute(
        text("UPDATE refresh_tokens SET revoked = true, revoked_at = :now WHERE user_id = :uid"),
        {"now": datetime.utcnow(), "uid": user_id},
    )

    # Invalidate sessions
    await db.execute(
        text("UPDATE sessions SET is_active = false WHERE user_id = :uid"),
        {"uid": user_id},
    )

    await db.commit()

    return {"message": "Logged out successfully"}


# Token Introspection
@app.post("/api/v1/oauth/introspect", response_model=TokenIntrospectResponse)
async def introspect_token(
    token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Introspect a token (OAuth2 Token Introspection)"""
    try:
        payload = token_service.verify_token(token)

        return TokenIntrospectResponse(
            active=True,
            scope=payload.get("scope"),
            client_id=payload.get("client_id"),
            username=payload.get("username"),
            token_type=payload.get("type"),
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            sub=payload.get("sub"),
        )
    except HTTPException:
        return TokenIntrospectResponse(active=False)


# User Info (OIDC)
@app.get("/api/v1/oauth/userinfo")
async def get_userinfo(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get user info (OIDC UserInfo endpoint)"""
    # Get roles
    roles_result = await db.execute(
        text(
            """SELECT r.name FROM roles r 
               JOIN user_roles ur ON r.id = ur.role_id 
               WHERE ur.user_id = :uid"""
        ),
        {"uid": current_user.id},
    )
    roles = [r[0] for r in roles_result.fetchall()]

    return {
        "sub": current_user.id,
        "preferred_username": current_user.username,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "phone_number": current_user.phone_number,
        "phone_number_verified": current_user.phone_verified,
        "roles": roles,
        "updated_at": int(current_user.updated_at.timestamp()),
    }


# Password Management
@app.post("/api/v1/auth/password/change")
async def change_password(
    request: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user password"""
    # Verify current password
    if not password_service.verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match",
        )

    is_valid, errors = password_service.validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"errors": errors})

    # Update password
    new_hash = password_service.hash_password(request.new_password)
    await db.execute(
        text(
            """UPDATE users 
               SET password_hash = :hash, 
                   last_password_change = :now,
                   password_expires_at = :expires
               WHERE id = :id"""
        ),
        {
            "hash": new_hash,
            "now": datetime.utcnow(),
            "expires": datetime.utcnow() + timedelta(days=90),
            "id": current_user.id,
        },
    )
    await db.commit()

    return {"message": "Password changed successfully"}


# MFA Setup
@app.post("/api/v1/auth/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Setup MFA for user"""
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    secret = mfa_service.generate_secret()
    qr_uri = mfa_service.generate_totp_uri(secret, current_user.username)
    backup_codes = mfa_service.generate_backup_codes()

    # Store secret temporarily (user must verify before enabling)
    await db.execute(
        text("UPDATE users SET mfa_secret = :secret WHERE id = :id"),
        {"secret": secret, "id": current_user.id},
    )
    await db.commit()

    return MFASetupResponse(secret=secret, qr_code_uri=qr_uri, backup_codes=backup_codes)


@app.post("/api/v1/auth/mfa/verify")
async def verify_mfa_setup(
    code: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify MFA setup and enable"""
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated",
        )

    if not mfa_service.verify_totp(current_user.mfa_secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    await db.execute(
        text("UPDATE users SET mfa_enabled = true WHERE id = :id"),
        {"id": current_user.id},
    )
    await db.commit()

    return {"message": "MFA enabled successfully"}


@app.post("/api/v1/auth/mfa/disable")
async def disable_mfa(
    code: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable MFA"""
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    if not mfa_service.verify_totp(current_user.mfa_secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    await db.execute(
        text("UPDATE users SET mfa_enabled = false, mfa_secret = NULL WHERE id = :id"),
        {"id": current_user.id},
    )
    await db.commit()

    return {"message": "MFA disabled successfully"}


# Role Management
@app.get("/api/v1/roles")
async def list_roles(db: AsyncSession = Depends(get_db)):
    """List all roles"""
    result = await db.execute(text("SELECT * FROM roles ORDER BY name"))
    roles = result.fetchall()

    return {
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "is_system_role": r.is_system_role,
            }
            for r in roles
        ]
    }


@app.post("/api/v1/roles")
async def create_role(
    request: RoleCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new role"""
    role = Role(name=request.name, description=request.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return {"id": role.id, "name": role.name, "description": role.description}


@app.post("/api/v1/users/{user_id}/roles/{role_id}")
async def assign_role(
    user_id: str,
    role_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign role to user"""
    # Check if already assigned
    result = await db.execute(
        text("SELECT id FROM user_roles WHERE user_id = :uid AND role_id = :rid"),
        {"uid": user_id, "rid": role_id},
    )
    if result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already assigned",
        )

    user_role = UserRole(user_id=user_id, role_id=role_id, granted_by=current_user.id)
    db.add(user_role)
    await db.commit()

    return {"message": "Role assigned successfully"}


@app.delete("/api/v1/users/{user_id}/roles/{role_id}")
async def revoke_role(
    user_id: str,
    role_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke role from user"""
    await db.execute(
        text("DELETE FROM user_roles WHERE user_id = :uid AND role_id = :rid"),
        {"uid": user_id, "rid": role_id},
    )
    await db.commit()

    return {"message": "Role revoked successfully"}


# Sessions Management
@app.get("/api/v1/sessions")
async def list_sessions(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List user sessions"""
    result = await db.execute(
        text(
            """SELECT * FROM sessions 
               WHERE user_id = :uid AND is_active = true 
               ORDER BY last_activity DESC"""
        ),
        {"uid": current_user.id},
    )
    sessions = result.fetchall()

    return {
        "sessions": [
            {
                "id": s.id,
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "device_id": s.device_id,
                "last_activity": s.last_activity.isoformat(),
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ]
    }


@app.delete("/api/v1/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session"""
    await db.execute(
        text("UPDATE sessions SET is_active = false WHERE id = :sid AND user_id = :uid"),
        {"sid": session_id, "uid": current_user.id},
    )
    await db.commit()

    return {"message": "Session revoked"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
