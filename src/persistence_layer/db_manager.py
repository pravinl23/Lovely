"""
Database manager for handling all persistence operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, or_, func, desc
import json
from cryptography.fernet import Fernet
import numpy as np

from config.settings import settings
from src.persistence_layer.models import (
    Base, User, Contact, Message, Fact, OutboundReply, 
    Briefing, MessageEmbedding, ProgressionStage
)
from src.perception_layer.models import Message as PerceptionMessage
from src.utils.logging import get_logger
from src.utils.embeddings import EmbeddingGenerator

logger = get_logger(__name__)


class DatabaseManager:
    """Manages all database operations"""
    
    def __init__(self):
        # Parse database URL and add SSL if connecting to Supabase
        db_url = settings.database_url
        
        # Add SSL mode for Supabase (detects supabase.co in URL)
        if 'supabase.co' in db_url and 'sslmode' not in db_url:
            db_url += '?sslmode=require'
        
        # Create engine with proper pooling for cloud databases
        self.engine = create_async_engine(
            db_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=300,  # Recycle connections every 5 minutes
            connect_args={
                "server_settings": {"jit": "off"},  # Disable JIT for better compatibility
                "command_timeout": 60,
            } if 'supabase.co' in db_url else {}
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Initialize encryption
        self.fernet = Fernet(settings.encryption_key.get_secret_value().encode())
        
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator()
        
    async def __aenter__(self):
        await self.initialize_database()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.engine.dispose()
    
    async def initialize_database(self):
        """Create all tables if they don't exist"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    # User operations
    async def create_user(
        self, 
        email: str, 
        hashed_password: str,
        whatsapp_phone_number_id: str,
        whatsapp_api_token: str
    ) -> User:
        """Create a new user"""
        async with self.async_session() as session:
            user = User(
                email=email,
                hashed_password=hashed_password,
                whatsapp_phone_number_id=whatsapp_phone_number_id,
                whatsapp_api_token=self.encrypt_data(whatsapp_api_token)
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        async with self.async_session() as session:
            return await session.get(User, user_id)
    
    async def get_user_by_phone_id(self, phone_number_id: str) -> Optional[User]:
        """Get user by WhatsApp phone number ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.whatsapp_phone_number_id == phone_number_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_outbound_messages(
        self,
        user_id: int,
        limit: int = 100
    ) -> List[Message]:
        """Get user's outbound messages"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Message).where(
                    and_(
                        Message.user_id == user_id,
                        Message.is_inbound == False
                    )
                ).order_by(desc(Message.timestamp)).limit(limit)
            )
            return result.scalars().all()
    
    async def get_recent_outbound_messages(
        self,
        contact_id: int,
        limit: int = 5
    ) -> List[Message]:
        """Get recent outbound messages for a contact"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Message).where(
                    and_(
                        Message.contact_id == contact_id,
                        Message.is_inbound == False
                    )
                ).order_by(desc(Message.timestamp)).limit(limit)
            )
            return result.scalars().all()
    
    # Contact operations
    async def get_or_create_contact(
        self,
        user_id: int,
        whatsapp_id: str,
        name: Optional[str] = None
    ) -> Contact:
        """Get existing contact or create new one"""
        async with self.async_session() as session:
            # Try to get existing
            result = await session.execute(
                select(Contact).where(
                    and_(
                        Contact.user_id == user_id,
                        Contact.whatsapp_id == whatsapp_id
                    )
                )
            )
            contact = result.scalar_one_or_none()
            
            if not contact:
                # Create new contact
                contact = Contact(
                    user_id=user_id,
                    whatsapp_id=whatsapp_id,
                    name=name
                )
                session.add(contact)
                await session.commit()
                await session.refresh(contact)
                
            return contact
    
    async def update_contact_metrics(
        self,
        contact_id: int,
        last_inbound_message_at: Optional[datetime] = None,
        last_ai_reply_at: Optional[datetime] = None
    ):
        """Update contact metrics"""
        async with self.async_session() as session:
            contact = await session.get(Contact, contact_id)
            if contact:
                if last_inbound_message_at:
                    contact.last_inbound_message_at = last_inbound_message_at
                if last_ai_reply_at:
                    contact.last_ai_reply_at = last_ai_reply_at
                    
                # Calculate metrics
                await self._calculate_contact_metrics(session, contact)
                
                await session.commit()
    
    async def _calculate_contact_metrics(self, session: AsyncSession, contact: Contact):
        """Calculate and update contact metrics"""
        # Get recent messages
        result = await session.execute(
            select(Message).where(
                Message.contact_id == contact.id
            ).order_by(desc(Message.timestamp)).limit(100)
        )
        messages = result.scalars().all()
        
        if messages:
            # Calculate response latency
            response_times = []
            for i in range(len(messages) - 1):
                if messages[i].is_inbound and not messages[i+1].is_inbound:
                    delta = messages[i+1].timestamp - messages[i].timestamp
                    response_times.append(delta.total_seconds())
            
            if response_times:
                contact.response_latency_avg = sum(response_times) / len(response_times)
            
            # Calculate reciprocity ratio
            inbound_count = sum(1 for m in messages if m.is_inbound)
            outbound_count = len(messages) - inbound_count
            
            if outbound_count > 0:
                contact.reciprocity_ratio = inbound_count / outbound_count
    
    # Message operations
    async def store_message(self, perception_message: PerceptionMessage) -> Message:
        """Store a message from the perception layer"""
        async with self.async_session() as session:
            # Get user from phone number ID
            # For now, assume we have a way to map this
            # In production, you'd track which user owns which phone number
            user_id = 1  # Placeholder
            
            # Get or create contact
            contact = await self.get_or_create_contact(
                user_id=user_id,
                whatsapp_id=perception_message.sender_id if perception_message.is_inbound 
                else perception_message.conversation_id
            )
            
            # Create message record
            message = Message(
                contact_id=contact.id,
                user_id=user_id,
                whatsapp_message_id=perception_message.message_id,
                timestamp=perception_message.timestamp,
                is_inbound=perception_message.is_inbound,
                text_content=perception_message.text_content,
                media_type=perception_message.media_type,
                media_url=perception_message.media_url,
                extracted_intents_json=[i.value for i in perception_message.annotations.intents]
                    if perception_message.annotations else None,
                extracted_entities_json=perception_message.annotations.to_dict()["entities"]
                    if perception_message.annotations else None,
                sentiment=perception_message.annotations.sentiment.value
                    if perception_message.annotations and perception_message.annotations.sentiment else None,
                raw_webhook_payload_json=self._redact_webhook_payload(perception_message.raw_webhook_payload)
            )
            
            session.add(message)
            await session.commit()
            await session.refresh(message)
            
            # Update contact metrics
            if perception_message.is_inbound:
                await self.update_contact_metrics(
                    contact_id=contact.id,
                    last_inbound_message_at=perception_message.timestamp
                )
            
            return message
    
    def _redact_webhook_payload(self, payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Redact sensitive information from webhook payload"""
        if not payload:
            return None
            
        # Create a copy to avoid modifying original
        redacted = json.loads(json.dumps(payload))
        
        # Redact sensitive fields
        sensitive_fields = ["from", "phone_number_id", "whatsapp_id"]
        
        def redact_dict(d: dict):
            for key in list(d.keys()):
                if key in sensitive_fields:
                    d[key] = "[REDACTED]"
                elif isinstance(d[key], dict):
                    redact_dict(d[key])
                elif isinstance(d[key], list):
                    for item in d[key]:
                        if isinstance(item, dict):
                            redact_dict(item)
        
        redact_dict(redacted)
        return redacted
    
    async def get_recent_messages(
        self,
        contact_id: int,
        limit: int = 20,
        before_timestamp: Optional[datetime] = None
    ) -> List[Message]:
        """Get recent messages for a contact"""
        async with self.async_session() as session:
            query = select(Message).where(
                Message.contact_id == contact_id
            )
            
            if before_timestamp:
                query = query.where(Message.timestamp < before_timestamp)
                
            query = query.order_by(desc(Message.timestamp)).limit(limit)
            
            result = await session.execute(query)
            messages = result.scalars().all()
            
            # Return in chronological order
            return list(reversed(messages))
    
    # Embedding operations
    async def store_message_embedding(
        self,
        message_id: str,
        text: str
    ):
        """Generate and store embedding for a message"""
        try:
            # Generate embedding
            embedding_vector = await self.embedding_generator.generate_embedding(text)
            
            async with self.async_session() as session:
                # Get the message's database ID
                result = await session.execute(
                    select(Message.id).where(
                        Message.whatsapp_message_id == message_id
                    )
                )
                db_message_id = result.scalar_one_or_none()
                
                if not db_message_id:
                    logger.error(f"Message not found: {message_id}")
                    return
                
                # Store embedding
                embedding = MessageEmbedding(
                    message_id=db_message_id,
                    embedding_model=self.embedding_generator.model_name,
                    embedding_dimension=len(embedding_vector),
                    embedding_vector=embedding_vector.tolist()
                )
                
                session.add(embedding)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}", exc_info=True)
    
    async def search_similar_messages(
        self,
        query_text: str,
        contact_id: int,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Message]:
        """Search for similar messages using embeddings"""
        # Generate query embedding
        query_embedding = await self.embedding_generator.generate_embedding(query_text)
        query_model = self.embedding_generator.model_name
        query_dimension = len(query_embedding)
        
        async with self.async_session() as session:
            # Get all embeddings for the contact with matching model/dimension
            result = await session.execute(
                select(MessageEmbedding, Message).join(Message).where(
                    and_(
                        Message.contact_id == contact_id,
                        MessageEmbedding.embedding_model == query_model,
                        MessageEmbedding.embedding_dimension == query_dimension
                    )
                ).options(selectinload(Message.contact))
            )
            
            embeddings_with_messages = result.all()
            
            # Calculate similarities
            similarities = []
            for embedding, message in embeddings_with_messages:
                stored_vector = np.array(embedding.embedding_vector)
                
                # Double-check dimension compatibility
                if len(stored_vector) != query_dimension:
                    logger.warning(f"Dimension mismatch: stored={len(stored_vector)}, query={query_dimension}")
                    continue
                
                similarity = self._cosine_similarity(query_embedding, stored_vector)
                
                if similarity >= threshold:
                    similarities.append((similarity, message))
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x[0], reverse=True)
            return [message for _, message in similarities[:limit]]
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)
    
    # Fact operations
    async def get_contact_facts(
        self,
        contact_id: int,
        limit: Optional[int] = None
    ) -> List[Fact]:
        """Get facts for a contact, ordered by relevance"""
        async with self.async_session() as session:
            query = select(Fact).where(
                Fact.contact_id == contact_id
            ).order_by(
                desc(Fact.last_reinforced),
                desc(Fact.decay_weight)
            )
            
            if limit:
                query = query.limit(limit)
                
            result = await session.execute(query)
            return result.scalars().all()
    
    async def update_contact_facts(
        self,
        contact_id: int,
        new_facts: List[Dict[str, Any]],
        reinforced_facts: List[Dict[str, Any]],
        conflicted_facts: List[Dict[str, Any]],
        origin_message_id: int
    ):
        """Update facts based on cognition layer processing"""
        async with self.async_session() as session:
            # Add new facts
            for fact_data in new_facts:
                fact = Fact(
                    contact_id=contact_id,
                    user_id=(await session.get(Contact, contact_id)).user_id,
                    key=fact_data["key"],
                    value=fact_data["value"],
                    origin_message_id=origin_message_id,
                    extraction_confidence=fact_data.get("confidence", 1.0)
                )
                session.add(fact)
            
            # Reinforce existing facts
            for fact_data in reinforced_facts:
                result = await session.execute(
                    select(Fact).where(
                        and_(
                            Fact.contact_id == contact_id,
                            Fact.key == fact_data["key"]
                        )
                    ).order_by(desc(Fact.version)).limit(1)
                )
                fact = result.scalar_one_or_none()
                
                if fact:
                    fact.last_reinforced = datetime.utcnow()
                    fact.decay_weight = min(fact.decay_weight * 1.1, 2.0)  # Increase weight
            
            # Handle conflicts
            for conflict in conflicted_facts:
                # Create new version
                result = await session.execute(
                    select(Fact).where(
                        and_(
                            Fact.contact_id == contact_id,
                            Fact.key == conflict["key"]
                        )
                    ).order_by(desc(Fact.version)).limit(1)
                )
                old_fact = result.scalar_one_or_none()
                
                if old_fact:
                    # Create new version
                    new_fact = Fact(
                        contact_id=contact_id,
                        user_id=old_fact.user_id,
                        key=conflict["key"],
                        value=conflict["new_value"],
                        origin_message_id=origin_message_id,
                        version=old_fact.version + 1
                    )
                    session.add(new_fact)
                    
                    # Reduce weight of old fact
                    old_fact.decay_weight *= 0.5
            
            await session.commit()
    
    # Briefing operations
    async def create_briefing(
        self,
        user_id: int,
        contact_id: int,
        stage_snapshot: Dict[str, Any],
        briefing_text: str
    ) -> Briefing:
        """Create a new briefing"""
        async with self.async_session() as session:
            briefing = Briefing(
                user_id=user_id,
                contact_id=contact_id,
                stage_snapshot_json=stage_snapshot,
                briefing_text=briefing_text
            )
            session.add(briefing)
            await session.commit()
            await session.refresh(briefing)
            return briefing
    
    async def mark_briefing_sent(self, briefing_id: int):
        """Mark briefing as sent"""
        async with self.async_session() as session:
            briefing = await session.get(Briefing, briefing_id)
            if briefing:
                briefing.email_sent_at = datetime.utcnow() 