"""
M1 - Identity Service Event Handlers
Handles publishing and consuming events for the identity service.
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publishes domain events to the event store.
    In production, this would integrate with PostgreSQL event store.
    """
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.service_name = os.getenv("SERVICE_NAME", "identity-service")
        
    async def publish(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publish an event to the event store.
        
        Args:
            event_type: Type of the event (e.g., USER_CREATED)
            aggregate_type: Type of aggregate (e.g., User)
            aggregate_id: ID of the aggregate
            payload: Event data
            metadata: Additional metadata
            
        Returns:
            Event ID
        """
        event_id = str(uuid.uuid4())
        
        event = {
            "id": event_id,
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "metadata": {
                "source_service": self.service_name,
                "correlation_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            },
            "version": 1,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # In production, save to PostgreSQL event store
        # For now, log the event
        logger.info(f"Publishing event: {event_type} for {aggregate_type}:{aggregate_id}")
        logger.debug(f"Event payload: {json.dumps(event, default=str)}")
        
        # Simulate database insert
        await self._save_to_event_store(event)
        
        return event_id
    
    async def _save_to_event_store(self, event: Dict[str, Any]) -> None:
        """
        Save event to PostgreSQL event store.
        
        In production, this would execute:
        INSERT INTO events (id, event_type, aggregate_type, aggregate_id, payload, metadata, version, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        # Mock implementation - in production use asyncpg or similar
        logger.info(f"Event {event['id']} saved to event store")
        
    async def publish_batch(self, events: list) -> list:
        """Publish multiple events in a single transaction."""
        event_ids = []
        for event_data in events:
            event_id = await self.publish(**event_data)
            event_ids.append(event_id)
        return event_ids


class EventConsumer:
    """
    Consumes events from the event store.
    Used for building projections and reacting to domain events.
    """
    
    def __init__(self):
        self.handlers: Dict[str, list] = {}
        self.database_url = os.getenv("DATABASE_URL")
        
    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for a specific event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")
        
    async def process_event(self, event: Dict[str, Any]) -> None:
        """
        Process a single event by invoking registered handlers.
        """
        event_type = event.get("event_type")
        handlers = self.handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                await handler(event)
                logger.info(f"Processed event {event['id']} with handler {handler.__name__}")
            except Exception as e:
                logger.error(f"Error processing event {event['id']}: {str(e)}")
                raise
                
    async def start_consuming(self, from_position: Optional[int] = None):
        """
        Start consuming events from the event store.
        In production, this would poll or use LISTEN/NOTIFY.
        """
        logger.info("Starting event consumer...")
        # Implementation would poll events table or use PostgreSQL notifications


class EventStore:
    """
    Event store operations for querying and managing events.
    """
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        
    async def get_events_for_aggregate(
        self,
        aggregate_type: str,
        aggregate_id: str,
        from_version: int = 0
    ) -> list:
        """
        Retrieve all events for a specific aggregate.
        Used for rebuilding aggregate state.
        """
        # In production, execute:
        # SELECT * FROM events 
        # WHERE aggregate_type = $1 AND aggregate_id = $2 AND version > $3
        # ORDER BY version ASC
        logger.info(f"Fetching events for {aggregate_type}:{aggregate_id}")
        return []
    
    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Retrieve events by type with pagination."""
        logger.info(f"Fetching events of type {event_type}")
        return []
    
    async def get_events_since(
        self,
        since: datetime,
        event_types: Optional[list] = None
    ) -> list:
        """Retrieve events since a specific timestamp."""
        logger.info(f"Fetching events since {since}")
        return []


# Event handlers for identity service
async def handle_user_created(event: Dict[str, Any]) -> None:
    """
    Handle USER_CREATED event.
    - Send welcome email
    - Initialize user preferences
    - Trigger first-time user flow
    """
    user_id = event["payload"]["user_id"]
    email = event["payload"]["email"]
    logger.info(f"Handling USER_CREATED for user {user_id}")
    
    # Send welcome notification (would integrate with notification service)
    logger.info(f"Sending welcome email to {email}")


async def handle_kyc_verified(event: Dict[str, Any]) -> None:
    """
    Handle KYC_VERIFIED event.
    - Update user KYC level
    - Unlock features based on verification level
    - Notify user of successful verification
    """
    user_id = event["payload"]["user_id"]
    kyc_level = event["payload"]["kyc_level"]
    logger.info(f"Handling KYC_VERIFIED for user {user_id}, level: {kyc_level}")
    
    # Update user record
    # Notify card service to enable card issuance
    # Send notification to user


async def handle_kyc_rejected(event: Dict[str, Any]) -> None:
    """
    Handle KYC_REJECTED event.
    - Log rejection reason
    - Notify user with instructions
    - Schedule follow-up if applicable
    """
    user_id = event["payload"]["user_id"]
    reason = event["payload"]["rejection_reason"]
    logger.info(f"Handling KYC_REJECTED for user {user_id}, reason: {reason}")


# Initialize event consumer with handlers
def setup_event_handlers(consumer: EventConsumer) -> None:
    """Register all event handlers for the identity service."""
    consumer.register_handler("USER_CREATED", handle_user_created)
    consumer.register_handler("KYC_VERIFIED", handle_kyc_verified)
    consumer.register_handler("KYC_REJECTED", handle_kyc_rejected)
