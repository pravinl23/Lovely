"""
Policy gate for determining when and how to reply
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from src.persistence_layer.db_manager import DatabaseManager
from src.persistence_layer.models import Contact, Message, ProgressionStage
from src.perception_layer.models import MessageAnnotations, Sentiment, Intent
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


class PolicyDecision(Enum):
    """Policy decision types"""
    ALLOW = "allow"
    BLOCK_NOT_ENABLED = "block_not_enabled"
    BLOCK_TOO_RECENT = "block_too_recent"
    BLOCK_SENSITIVE = "block_sensitive"
    BLOCK_STAGE_SATURATED = "block_stage_saturated"
    BLOCK_OUTSIDE_WINDOW = "block_outside_window"
    DEFER_HUMAN_REVIEW = "defer_human_review"


class SensitivityLevel(Enum):
    """Message sensitivity levels"""
    SAFE = "safe"
    CAUTION = "caution"
    SENSITIVE = "sensitive"
    CRITICAL = "critical"


class PolicyGate:
    """Enforces policies for reply generation"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        
        # Configuration
        self.min_reply_interval = timedelta(seconds=settings.default_reply_delay_seconds)
        self.stage_attempt_limits = {
            ProgressionStage.LOGISTICS_CANDIDATE: 3,
            ProgressionStage.PROPOSAL: 3,
            ProgressionStage.NEGOTIATION: 5
        }
        
    async def __aenter__(self):
        await self.db_manager.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db_manager.__aexit__(exc_type, exc_val, exc_tb)
    
    async def evaluate_reply_permission(
        self,
        contact_id: int,
        message: Message,
        annotations: Optional[MessageAnnotations] = None
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """Evaluate whether AI should reply to a message"""
        
        # Get contact and user info
        async with self.db_manager.async_session() as session:
            contact = await session.get(Contact, contact_id)
            if not contact:
                return PolicyDecision.BLOCK_NOT_ENABLED, "Contact not found"
            
            from src.persistence_layer.models import User
            user = await session.get(User, contact.user_id)
            if not user:
                return PolicyDecision.BLOCK_NOT_ENABLED, "User not found"
        
        # Check 1: Global and per-contact AI enablement
        if not user.global_automation_enabled:
            return PolicyDecision.BLOCK_NOT_ENABLED, "Global automation disabled"
            
        if not contact.ai_enabled:
            return PolicyDecision.BLOCK_NOT_ENABLED, "AI not enabled for this contact"
        
        # Check 2: Recency check
        recency_decision = await self._check_recency(contact, message)
        if recency_decision[0] != PolicyDecision.ALLOW:
            return recency_decision
        
        # Check 3: Sensitivity screening
        sensitivity_decision = await self._check_sensitivity(message, annotations)
        if sensitivity_decision[0] != PolicyDecision.ALLOW:
            return sensitivity_decision
        
        # Check 4: Stage saturation
        saturation_decision = await self._check_stage_saturation(contact)
        if saturation_decision[0] != PolicyDecision.ALLOW:
            return saturation_decision
        
        # Check 5: 24-hour window (WhatsApp policy)
        window_decision = await self._check_24h_window(contact)
        if window_decision[0] != PolicyDecision.ALLOW:
            return window_decision
        
        # All checks passed
        return PolicyDecision.ALLOW, None
    
    async def _check_recency(
        self, 
        contact: Contact, 
        message: Message
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """Check if AI has replied too recently"""
        # Disable rate limiting for now - always allow replies to new messages
        # This prevents blocking legitimate conversation flow
        return PolicyDecision.ALLOW, None
    
    async def _check_sensitivity(
        self,
        message: Message,
        annotations: Optional[MessageAnnotations] = None
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """Check message sensitivity"""
        sensitivity_level = await self._assess_sensitivity(message, annotations)
        
        if sensitivity_level == SensitivityLevel.CRITICAL:
            return PolicyDecision.DEFER_HUMAN_REVIEW, "Critical sensitivity detected"
        elif sensitivity_level == SensitivityLevel.SENSITIVE:
            return PolicyDecision.BLOCK_SENSITIVE, "Sensitive content detected"
        
        return PolicyDecision.ALLOW, None
    
    async def _assess_sensitivity(
        self,
        message: Message,
        annotations: Optional[MessageAnnotations] = None
    ) -> SensitivityLevel:
        """Assess the sensitivity level of a message"""
        if not message.text_content:
            return SensitivityLevel.SAFE
            
        text_lower = message.text_content.lower()
        
        # Critical keywords (immediate human review)
        critical_keywords = [
            "emergency", "urgent", "help", "suicide", "kill", "die",
            "hospital", "accident", "police", "lawyer", "legal"
        ]
        
        if any(keyword in text_lower for keyword in critical_keywords):
            return SensitivityLevel.CRITICAL
        
        # Sensitive keywords (block AI)
        sensitive_keywords = [
            "money", "payment", "transfer", "bank", "credit card",
            "password", "secret", "confidential", "private",
            "medical", "disease", "pregnant", "diagnosis"
        ]
        
        if any(keyword in text_lower for keyword in sensitive_keywords):
            return SensitivityLevel.SENSITIVE
        
        # Check sentiment - only block if extremely negative with clear refusal/boundary intent
        if annotations and annotations.sentiment in [Sentiment.NEGATIVE, Sentiment.ANNOYED]:
            # Only block if it's explicitly a refusal or boundary setting
            dangerous_intents = [Intent.REFUSAL, Intent.BOUNDARY]
            if any(intent in dangerous_intents for intent in annotations.intents):
                # Still check if it's just normal conversation
                normal_negative_phrases = [
                    "not really", "don't like", "not into", "that sucks", "annoying",
                    "boring", "tired", "busy", "not today", "maybe later", "not sure"
                ]
                if any(phrase in text_lower for phrase in normal_negative_phrases):
                    return SensitivityLevel.SAFE  # Allow normal conversation
                return SensitivityLevel.CAUTION  # Reduced from SENSITIVE to CAUTION
        
        return SensitivityLevel.SAFE
    
    async def _check_stage_saturation(
        self,
        contact: Contact
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """Check if we've made too many attempts at current stage"""
        stage = contact.progression_stage
        
        if stage not in self.stage_attempt_limits:
            return PolicyDecision.ALLOW, None
            
        # Count recent attempts at this stage
        recent_messages = await self.db_manager.get_recent_messages(
            contact_id=contact.id,
            limit=50
        )
        
        # Look for patterns indicating repeated attempts
        attempt_count = 0
        stage_keywords = {
            ProgressionStage.LOGISTICS_CANDIDATE: ["meet", "hang out", "get together", "coffee", "drinks"],
            ProgressionStage.PROPOSAL: ["when", "where", "what time", "which day", "how about"],
            ProgressionStage.NEGOTIATION: ["instead", "maybe", "could we", "would you prefer"]
        }
        
        keywords = stage_keywords.get(stage, [])
        
        for msg in recent_messages:
            if not msg.is_inbound and msg.text_content:
                if any(kw in msg.text_content.lower() for kw in keywords):
                    attempt_count += 1
        
        limit = self.stage_attempt_limits[stage]
        if attempt_count >= limit:
            return PolicyDecision.BLOCK_STAGE_SATURATED, f"Already made {attempt_count} attempts at {stage.value}"
        
        return PolicyDecision.ALLOW, None
    
    async def _check_24h_window(
        self,
        contact: Contact
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """Check if we're within 24-hour customer service window"""
        if not contact.last_inbound_message_at:
            return PolicyDecision.ALLOW, None
            
        time_since_last_inbound = datetime.utcnow() - contact.last_inbound_message_at
        
        if time_since_last_inbound > timedelta(hours=24):
            return PolicyDecision.BLOCK_OUTSIDE_WINDOW, "Outside 24-hour window"
        
        return PolicyDecision.ALLOW, None
    
    async def get_reply_constraints(
        self,
        contact: Contact
    ) -> Dict[str, Any]:
        """Get constraints for reply generation based on current state"""
        constraints = {
            "max_length": 150,  # Default max length in words
            "tone_adjustment": None,
            "content_restrictions": [],
            "suggested_delay_seconds": 0
        }
        
        # Adjust based on progression stage
        if contact.progression_stage == ProgressionStage.DISCOVERY:
            constraints["tone_adjustment"] = "curious and friendly"
            constraints["content_restrictions"].append("avoid suggesting meetings")
            
        elif contact.progression_stage == ProgressionStage.RAPPORT:
            constraints["tone_adjustment"] = "warm and engaging"
            
        elif contact.progression_stage == ProgressionStage.LOGISTICS_CANDIDATE:
            constraints["tone_adjustment"] = "casual and suggestive"
            constraints["content_restrictions"].append("subtle meeting suggestions only")
            
        elif contact.progression_stage in [ProgressionStage.PROPOSAL, ProgressionStage.NEGOTIATION]:
            constraints["tone_adjustment"] = "accommodating and flexible"
            constraints["max_length"] = 100  # Shorter, more focused
            
        elif contact.progression_stage == ProgressionStage.CONFIRMATION:
            constraints["tone_adjustment"] = "excited and appreciative"
            constraints["content_restrictions"].append("avoid changing plans")
        
        # Adjust based on recent patterns
        if contact.response_latency_avg:
            # Match their response speed somewhat
            if contact.response_latency_avg < 60:  # Less than 1 minute avg
                constraints["suggested_delay_seconds"] = 30
            elif contact.response_latency_avg < 300:  # Less than 5 minutes
                constraints["suggested_delay_seconds"] = 120
            else:
                constraints["suggested_delay_seconds"] = 300
        
        return constraints 