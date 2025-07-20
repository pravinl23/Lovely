"""
Database models for the persistence layer
"""
from sqlalchemy import (
    Column, String, Integer, Boolean, Float, DateTime, Text, 
    ForeignKey, JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class ProgressionStage(enum.Enum):
    """Contact progression stages"""
    DISCOVERY = "discovery"
    RAPPORT = "rapport"
    LOGISTICS_CANDIDATE = "logistics_candidate"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CONFIRMATION = "confirmation"
    POST_CONFIRMATION = "post_confirmation"


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    whatsapp_phone_number_id = Column(String(255), unique=True)
    whatsapp_api_token = Column(Text)  # Encrypted
    global_automation_enabled = Column(Boolean, default=False)
    persona_profile_json = Column(JSON, default={})
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    facts = relationship("Fact", back_populates="user", cascade="all, delete-orphan")



class Contact(Base):
    """Contact (WhatsApp conversation) model"""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    whatsapp_id = Column(String(255), nullable=False)  # Phone number
    name = Column(String(255))
    ai_enabled = Column(Boolean, default=False)
    progression_stage = Column(
        SQLEnum(ProgressionStage), 
        default=ProgressionStage.DISCOVERY
    )
    
    # Metrics
    last_inbound_message_at = Column(DateTime)
    last_ai_reply_at = Column(DateTime)
    response_latency_avg = Column(Float)  # Average response time in seconds
    reciprocity_ratio = Column(Float)  # Ratio of inbound to outbound messages
    computed_metrics_json = Column(JSON, default={})
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="contacts")
    messages = relationship("Message", back_populates="contact", cascade="all, delete-orphan")
    facts = relationship("Fact", back_populates="contact", cascade="all, delete-orphan")
    outbound_replies = relationship("OutboundReply", back_populates="contact", cascade="all, delete-orphan")

    
    # Indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'whatsapp_id', name='unique_user_contact'),
        Index('idx_contact_user_whatsapp', 'user_id', 'whatsapp_id'),
    )


class Message(Base):
    """Message model"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    whatsapp_message_id = Column(String(255), unique=True, nullable=False)  # wamid
    
    timestamp = Column(DateTime, nullable=False)
    is_inbound = Column(Boolean, nullable=False)
    text_content = Column(Text)
    media_type = Column(String(50))
    media_url = Column(Text)
    
    # Extracted data
    extracted_intents_json = Column(JSON)
    extracted_entities_json = Column(JSON)
    sentiment = Column(String(50))
    raw_webhook_payload_json = Column(JSON)  # Redacted version
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="messages")
    contact = relationship("Contact", back_populates="messages")
    facts = relationship("Fact", back_populates="origin_message")
    outbound_reply = relationship("OutboundReply", back_populates="message", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_message_contact_timestamp', 'contact_id', 'timestamp'),
        Index('idx_message_whatsapp_id', 'whatsapp_message_id'),
    )


class Fact(Base):
    """Fact/knowledge about a contact"""
    __tablename__ = "facts"
    
    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    origin_message_id = Column(Integer, ForeignKey("messages.id"))
    
    extraction_confidence = Column(Float, default=1.0)
    first_observed = Column(DateTime, server_default=func.now())
    last_reinforced = Column(DateTime, server_default=func.now())
    decay_weight = Column(Float, default=1.0)
    version = Column(Integer, default=1)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="facts")
    contact = relationship("Contact", back_populates="facts")
    origin_message = relationship("Message", back_populates="facts")
    
    # Indexes
    __table_args__ = (
        Index('idx_fact_contact_key', 'contact_id', 'key'),
        Index('idx_fact_last_reinforced', 'last_reinforced'),
    )


class OutboundReply(Base):
    """Generated outbound replies"""
    __tablename__ = "outbound_replies"
    
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"))  # Reply to this message
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    generated_text = Column(Text, nullable=False)
    full_prompt_context_json = Column(JSON)  # Redacted version
    llm_meta_tags_json = Column(JSON)
    
    status = Column(String(50), nullable=False)  # sent, failed
    failure_reason = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User")
    contact = relationship("Contact", back_populates="outbound_replies")
    message = relationship("Message", back_populates="outbound_reply")





class MessageEmbedding(Base):
    """Vector embeddings for messages"""
    __tablename__ = "message_embeddings"
    
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"), unique=True, nullable=False)
    embedding_model = Column(String(100), nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    
    # Note: In production, you'd use a vector column type
    # For PostgreSQL with pgvector: Column(Vector(dimension))
    # For now, we'll store as JSON array
    embedding_vector = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_embedding_message', 'message_id'),
    ) 