"""
Ethio-Core Event Store
Kafka-based event sourcing with PostgreSQL persistence
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
import asyncpg

# ============================================================================
# Configuration
# ============================================================================

class Settings:
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/event_store"
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_GROUP_ID: str = "event-store-consumer"
    
settings = Settings()

# ============================================================================
# Event Types
# ============================================================================

class EventType(str, Enum):
    # Identity Events
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    CUSTOMER_VERIFIED = "customer.verified"
    CUSTOMER_SUSPENDED = "customer.suspended"
    KYC_INITIATED = "kyc.initiated"
    KYC_COMPLETED = "kyc.completed"
    KYC_FAILED = "kyc.failed"
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_VERIFIED = "document.verified"
    
    # Biometric Events
    BIOMETRIC_ENROLLED = "biometric.enrolled"
    BIOMETRIC_VERIFIED = "biometric.verified"
    BIOMETRIC_FAILED = "biometric.failed"
    LIVENESS_CHECKED = "liveness.checked"
    
    # Card Events
    CARD_REQUESTED = "card.requested"
    CARD_ISSUED = "card.issued"
    CARD_ACTIVATED = "card.activated"
    CARD_BLOCKED = "card.blocked"
    CARD_UNBLOCKED = "card.unblocked"
    CARD_EXPIRED = "card.expired"
    PIN_SET = "pin.set"
    PIN_CHANGED = "pin.changed"
    
    # Transaction Events
    TRANSACTION_INITIATED = "transaction.initiated"
    TRANSACTION_AUTHORIZED = "transaction.authorized"
    TRANSACTION_COMPLETED = "transaction.completed"
    TRANSACTION_FAILED = "transaction.failed"
    TRANSACTION_REVERSED = "transaction.reversed"
    
    # Security Events
    LOGIN_SUCCESS = "security.login.success"
    LOGIN_FAILED = "security.login.failed"
    MFA_CHALLENGED = "security.mfa.challenged"
    MFA_VERIFIED = "security.mfa.verified"
    FRAUD_DETECTED = "security.fraud.detected"
    ALERT_TRIGGERED = "security.alert.triggered"
    
    # SSO Events
    SESSION_CREATED = "sso.session.created"
    SESSION_REFRESHED = "sso.session.refreshed"
    SESSION_TERMINATED = "sso.session.terminated"
    TOKEN_ISSUED = "sso.token.issued"
    TOKEN_REVOKED = "sso.token.revoked"

# ============================================================================
# Models
# ============================================================================

class EventBase(BaseModel):
    event_type: EventType
    aggregate_id: str
    aggregate_type: str
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class EventResponse(BaseModel):
    id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]]
    correlation_id: Optional[str]
    causation_id: Optional[str]
    version: int
    timestamp: datetime

class EventStream(BaseModel):
    aggregate_id: str
    aggregate_type: str
    events: List[EventResponse]
    current_version: int

class Snapshot(BaseModel):
    aggregate_id: str
    aggregate_type: str
    state: Dict[str, Any]
    version: int
    timestamp: datetime

# ============================================================================
# Database
# ============================================================================

class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=5,
            max_size=20
        )
        await self._create_tables()
    
    async def disconnect(self):
        if self.pool:
            await self.pool.close()
    
    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id UUID PRIMARY KEY,
                    event_type VARCHAR(100) NOT NULL,
                    aggregate_id VARCHAR(100) NOT NULL,
                    aggregate_type VARCHAR(50) NOT NULL,
                    payload JSONB NOT NULL,
                    metadata JSONB,
                    correlation_id VARCHAR(100),
                    causation_id VARCHAR(100),
                    version INTEGER NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_aggregate 
                ON events(aggregate_id, aggregate_type);
                
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON events(event_type);
                
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_events_correlation 
                ON events(correlation_id);
                
                CREATE TABLE IF NOT EXISTS snapshots (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    aggregate_id VARCHAR(100) NOT NULL,
                    aggregate_type VARCHAR(50) NOT NULL,
                    state JSONB NOT NULL,
                    version INTEGER NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(aggregate_id, aggregate_type)
                );
                
                CREATE INDEX IF NOT EXISTS idx_snapshots_aggregate 
                ON snapshots(aggregate_id, aggregate_type);
                
                CREATE TABLE IF NOT EXISTS projections (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    projection_name VARCHAR(100) NOT NULL,
                    last_processed_event_id UUID,
                    last_processed_timestamp TIMESTAMPTZ,
                    state JSONB,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(projection_name)
                );
            """)
    
    async def store_event(self, event: Event) -> EventResponse:
        async with self.pool.acquire() as conn:
            # Get current version for optimistic concurrency
            current_version = await conn.fetchval("""
                SELECT COALESCE(MAX(version), 0) 
                FROM events 
                WHERE aggregate_id = $1 AND aggregate_type = $2
            """, event.aggregate_id, event.aggregate_type)
            
            new_version = current_version + 1
            
            await conn.execute("""
                INSERT INTO events (
                    id, event_type, aggregate_id, aggregate_type,
                    payload, metadata, correlation_id, causation_id,
                    version, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                uuid.UUID(event.id),
                event.event_type.value,
                event.aggregate_id,
                event.aggregate_type,
                json.dumps(event.payload),
                json.dumps(event.metadata) if event.metadata else None,
                event.correlation_id,
                event.causation_id,
                new_version,
                event.timestamp
            )
            
            return EventResponse(
                id=event.id,
                event_type=event.event_type.value,
                aggregate_id=event.aggregate_id,
                aggregate_type=event.aggregate_type,
                payload=event.payload,
                metadata=event.metadata,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                version=new_version,
                timestamp=event.timestamp
            )
    
    async def get_events(
        self,
        aggregate_id: str,
        aggregate_type: str,
        from_version: int = 0
    ) -> List[EventResponse]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM events
                WHERE aggregate_id = $1 AND aggregate_type = $2 AND version > $3
                ORDER BY version ASC
            """, aggregate_id, aggregate_type, from_version)
            
            return [
                EventResponse(
                    id=str(row['id']),
                    event_type=row['event_type'],
                    aggregate_id=row['aggregate_id'],
                    aggregate_type=row['aggregate_type'],
                    payload=json.loads(row['payload']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else None,
                    correlation_id=row['correlation_id'],
                    causation_id=row['causation_id'],
                    version=row['version'],
                    timestamp=row['timestamp']
                )
                for row in rows
            ]
    
    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[EventResponse]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM events
                WHERE event_type = $1
                ORDER BY timestamp DESC
                LIMIT $2 OFFSET $3
            """, event_type, limit, offset)
            
            return [
                EventResponse(
                    id=str(row['id']),
                    event_type=row['event_type'],
                    aggregate_id=row['aggregate_id'],
                    aggregate_type=row['aggregate_type'],
                    payload=json.loads(row['payload']),
                    metadata=json.loads(row['metadata']) if row['metadata'] else None,
                    correlation_id=row['correlation_id'],
                    causation_id=row['causation_id'],
                    version=row['version'],
                    timestamp=row['timestamp']
                )
                for row in rows
            ]
    
    async def save_snapshot(self, snapshot: Snapshot):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO snapshots (aggregate_id, aggregate_type, state, version, timestamp)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (aggregate_id, aggregate_type) 
                DO UPDATE SET state = $3, version = $4, timestamp = $5
            """,
                snapshot.aggregate_id,
                snapshot.aggregate_type,
                json.dumps(snapshot.state),
                snapshot.version,
                snapshot.timestamp
            )
    
    async def get_snapshot(
        self,
        aggregate_id: str,
        aggregate_type: str
    ) -> Optional[Snapshot]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM snapshots
                WHERE aggregate_id = $1 AND aggregate_type = $2
            """, aggregate_id, aggregate_type)
            
            if row:
                return Snapshot(
                    aggregate_id=row['aggregate_id'],
                    aggregate_type=row['aggregate_type'],
                    state=json.loads(row['state']),
                    version=row['version'],
                    timestamp=row['timestamp']
                )
            return None

# ============================================================================
# Kafka Producer/Consumer
# ============================================================================

class KafkaManager:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.admin: Optional[AIOKafkaAdminClient] = None
    
    async def connect(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        
        # Create topics
        self.admin = AIOKafkaAdminClient(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
        )
        await self.admin.start()
        
        topics = [
            NewTopic("identity-events", num_partitions=3, replication_factor=1),
            NewTopic("biometric-events", num_partitions=3, replication_factor=1),
            NewTopic("card-events", num_partitions=3, replication_factor=1),
            NewTopic("transaction-events", num_partitions=3, replication_factor=1),
            NewTopic("security-events", num_partitions=3, replication_factor=1),
            NewTopic("sso-events", num_partitions=3, replication_factor=1),
            NewTopic("dead-letter-queue", num_partitions=1, replication_factor=1),
        ]
        
        try:
            await self.admin.create_topics(topics)
        except Exception:
            pass  # Topics may already exist
    
    async def disconnect(self):
        if self.producer:
            await self.producer.stop()
        if self.admin:
            await self.admin.close()
        for consumer in self.consumers.values():
            await consumer.stop()
    
    def get_topic_for_event(self, event_type: str) -> str:
        if event_type.startswith("customer") or event_type.startswith("kyc") or event_type.startswith("document"):
            return "identity-events"
        elif event_type.startswith("biometric") or event_type.startswith("liveness"):
            return "biometric-events"
        elif event_type.startswith("card") or event_type.startswith("pin"):
            return "card-events"
        elif event_type.startswith("transaction"):
            return "transaction-events"
        elif event_type.startswith("security"):
            return "security-events"
        elif event_type.startswith("sso"):
            return "sso-events"
        return "dead-letter-queue"
    
    async def publish_event(self, event: EventResponse):
        topic = self.get_topic_for_event(event.event_type)
        await self.producer.send_and_wait(
            topic,
            value={
                "id": event.id,
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "aggregate_type": event.aggregate_type,
                "payload": event.payload,
                "metadata": event.metadata,
                "correlation_id": event.correlation_id,
                "causation_id": event.causation_id,
                "version": event.version,
                "timestamp": event.timestamp.isoformat()
            },
            key=event.aggregate_id.encode('utf-8')
        )

# ============================================================================
# Application
# ============================================================================

db = DatabaseManager()
kafka = KafkaManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await kafka.connect()
    yield
    await db.disconnect()
    await kafka.disconnect()

app = FastAPI(
    title="Ethio-Core Event Store",
    description="Event sourcing and CQRS infrastructure for Ethio-Core banking platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "event-store"}

@app.post("/events", response_model=EventResponse)
async def store_event(
    event_data: EventCreate,
    background_tasks: BackgroundTasks
):
    """Store a new event and publish to Kafka"""
    event = Event(
        event_type=event_data.event_type,
        aggregate_id=event_data.aggregate_id,
        aggregate_type=event_data.aggregate_type,
        payload=event_data.payload,
        metadata=event_data.metadata,
        correlation_id=event_data.correlation_id,
        causation_id=event_data.causation_id
    )
    
    stored_event = await db.store_event(event)
    background_tasks.add_task(kafka.publish_event, stored_event)
    
    return stored_event

@app.get("/events/stream/{aggregate_type}/{aggregate_id}", response_model=EventStream)
async def get_event_stream(
    aggregate_type: str,
    aggregate_id: str,
    from_version: int = Query(0, ge=0)
):
    """Get all events for an aggregate"""
    events = await db.get_events(aggregate_id, aggregate_type, from_version)
    current_version = events[-1].version if events else 0
    
    return EventStream(
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        events=events,
        current_version=current_version
    )

@app.get("/events/type/{event_type}", response_model=List[EventResponse])
async def get_events_by_type(
    event_type: str,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get events by type with pagination"""
    return await db.get_events_by_type(event_type, limit, offset)

@app.post("/snapshots")
async def save_snapshot(snapshot: Snapshot):
    """Save an aggregate snapshot"""
    await db.save_snapshot(snapshot)
    return {"status": "saved"}

@app.get("/snapshots/{aggregate_type}/{aggregate_id}", response_model=Optional[Snapshot])
async def get_snapshot(aggregate_type: str, aggregate_id: str):
    """Get the latest snapshot for an aggregate"""
    snapshot = await db.get_snapshot(aggregate_id, aggregate_type)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot

@app.get("/replay/{aggregate_type}/{aggregate_id}")
async def replay_aggregate(
    aggregate_type: str,
    aggregate_id: str
):
    """Replay events to rebuild aggregate state"""
    # Get snapshot if available
    snapshot = await db.get_snapshot(aggregate_id, aggregate_type)
    from_version = snapshot.version if snapshot else 0
    initial_state = snapshot.state if snapshot else {}
    
    # Get events since snapshot
    events = await db.get_events(aggregate_id, aggregate_type, from_version)
    
    return {
        "aggregate_id": aggregate_id,
        "aggregate_type": aggregate_type,
        "initial_state": initial_state,
        "events_to_replay": len(events),
        "from_version": from_version,
        "events": events
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
