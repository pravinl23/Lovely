"""
Message models and data structures for the Perception Layer
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Literal
from enum import Enum
import json

MediaType = Literal["text", "image", "audio", "video", "document", "sticker", "location", "unknown"]


class Intent(Enum):
    """Message intent types"""
    BANTER = "banter"
    LOGISTICS = "logistics"
    SCHEDULING = "scheduling"
    QUESTION = "question"
    SHARING_INFO = "sharing_info"
    BOUNDARY = "boundary"
    REFUSAL = "refusal"
    ENTHUSIASM = "enthusiasm"
    ACKNOWLEDGEMENT = "acknowledgement"
    GREETING = "greeting"
    FAREWELL = "farewell"
    UNKNOWN = "unknown"


class Sentiment(Enum):
    """Message sentiment types"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    EXCITED = "excited"
    ANNOYED = "annoyed"
    CURIOUS = "curious"
    WARM = "warm"
    COLD = "cold"


@dataclass
class Entity:
    """Extracted entity from message"""
    type: str  # person, location, date, time, food, hobby, job_title, event, object
    value: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalMention:
    """Temporal reference in message"""
    original_text: str
    normalized_value: Optional[str] = None  # ISO 8601 format
    relative_reference: Optional[str] = None  # e.g., "tomorrow", "next week"
    confidence: float = 1.0


@dataclass
class MessageAnnotations:
    """Semantic annotations for a message"""
    intents: List[Intent] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    temporal_mentions: List[TemporalMention] = field(default_factory=list)
    sentiment: Optional[Sentiment] = None
    key_phrases: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "intents": [intent.value for intent in self.intents],
            "entities": [
                {
                    "type": entity.type,
                    "value": entity.value,
                    "confidence": entity.confidence,
                    "metadata": entity.metadata
                }
                for entity in self.entities
            ],
            "temporal_mentions": [
                {
                    "original_text": tm.original_text,
                    "normalized_value": tm.normalized_value,
                    "relative_reference": tm.relative_reference,
                    "confidence": tm.confidence
                }
                for tm in self.temporal_mentions
            ],
            "sentiment": self.sentiment.value if self.sentiment else None,
            "key_phrases": self.key_phrases,
            "questions": self.questions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageAnnotations":
        """Create from dictionary"""
        return cls(
            intents=[Intent(i) for i in data.get("intents", [])],
            entities=[
                Entity(
                    type=e["type"],
                    value=e["value"],
                    confidence=e.get("confidence", 1.0),
                    metadata=e.get("metadata", {})
                )
                for e in data.get("entities", [])
            ],
            temporal_mentions=[
                TemporalMention(
                    original_text=tm["original_text"],
                    normalized_value=tm.get("normalized_value"),
                    relative_reference=tm.get("relative_reference"),
                    confidence=tm.get("confidence", 1.0)
                )
                for tm in data.get("temporal_mentions", [])
            ],
            sentiment=Sentiment(data["sentiment"]) if data.get("sentiment") else None,
            key_phrases=data.get("key_phrases", []),
            questions=data.get("questions", [])
        )


@dataclass
class Message:
    """Canonical message representation"""
    message_id: str  # WhatsApp's wamid
    conversation_id: str  # Contact ID for simplicity
    sender_id: str  # WhatsApp ID of sender
    receiver_id: str  # Our bot's WhatsApp ID
    timestamp: datetime
    text_content: str  # Main text or extracted text from media
    media_type: MediaType = "text"
    media_url: Optional[str] = None
    media_id: Optional[str] = None
    is_inbound: bool = True
    raw_webhook_payload: Optional[Dict[str, Any]] = None
    annotations: Optional[MessageAnnotations] = None
    
    # Additional metadata
    caption: Optional[str] = None
    filename: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None
    reaction_data: Optional[Dict[str, Any]] = None
    interactive_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "timestamp": self.timestamp.isoformat(),
            "text_content": self.text_content,
            "media_type": self.media_type,
            "media_url": self.media_url,
            "media_id": self.media_id,
            "is_inbound": self.is_inbound,
            "raw_webhook_payload": self.raw_webhook_payload,
            "annotations": self.annotations.to_dict() if self.annotations else None,
            "caption": self.caption,
            "filename": self.filename,
            "location_data": self.location_data,
            "reaction_data": self.reaction_data,
            "interactive_data": self.interactive_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary"""
        return cls(
            message_id=data["message_id"],
            conversation_id=data["conversation_id"],
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            text_content=data["text_content"],
            media_type=data.get("media_type", "text"),
            media_url=data.get("media_url"),
            media_id=data.get("media_id"),
            is_inbound=data.get("is_inbound", True),
            raw_webhook_payload=data.get("raw_webhook_payload"),
            annotations=MessageAnnotations.from_dict(data["annotations"]) if data.get("annotations") else None,
            caption=data.get("caption"),
            filename=data.get("filename"),
            location_data=data.get("location_data"),
            reaction_data=data.get("reaction_data"),
            interactive_data=data.get("interactive_data")
        )
    
    def get_display_text(self) -> str:
        """Get the main text content for display"""
        if self.text_content:
            return self.text_content
        elif self.caption:
            return f"[{self.media_type}] {self.caption}"
        elif self.media_type != "text":
            return f"[{self.media_type}]"
        else:
            return "" 