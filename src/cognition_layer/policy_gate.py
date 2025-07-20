"""
Policy gate for enforcing reply policies
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import random

from src.persistence_layer.supabase_manager import SupabaseManager
from src.persistence_layer.models import Contact, Message, ProgressionStage
from src.perception_layer.models import MessageAnnotations, Sentiment, Intent
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


class PolicyDecision(Enum):
    """Policy decision types"""
    ALLOW = "allow"
    BLOCK_NOT_ENABLED = "block_not_enabled"
    BLOCK_SENSITIVE = "block_sensitive"
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
        self.db_manager = SupabaseManager()
        
    async def __aenter__(self):
        await self.db_manager.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db_manager.__aexit__(exc_type, exc_val, exc_tb)
    
    async def evaluate_reply_permission(
        self,
        contact_id: int,
        message: Dict[str, Any],
        annotations: Optional[MessageAnnotations] = None
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """Evaluate whether AI should reply to a message"""
        
        # Get contact and user info
        contact = await self.db_manager.get_contact_by_id(contact_id)
        if not contact:
            return PolicyDecision.BLOCK_NOT_ENABLED, "Contact not found"
        
        user = await self.db_manager.get_user_by_id(contact['user_id'])
        if not user:
            return PolicyDecision.BLOCK_NOT_ENABLED, "User not found"
        
        # Check 1: Global and per-contact AI enablement
        if not user.get('global_automation_enabled', False):
            return PolicyDecision.BLOCK_NOT_ENABLED, "Global automation disabled"
            
        if not contact.get('ai_enabled', False):
            return PolicyDecision.BLOCK_NOT_ENABLED, "AI not enabled for this contact"
        
        # Check 2: Sensitivity screening (only critical issues)
        sensitivity_decision = await self._check_sensitivity(message, annotations)
        if sensitivity_decision[0] != PolicyDecision.ALLOW:
            return sensitivity_decision
        
        # All checks passed - allow reply
        return PolicyDecision.ALLOW, None
    
    async def _check_sensitivity(
        self,
        message: Dict[str, Any],
        annotations: Optional[MessageAnnotations] = None
    ) -> Tuple[PolicyDecision, Optional[str]]:
        """Check message sensitivity - only block critical issues"""
        sensitivity_level = await self._assess_sensitivity(message, annotations)
        
        if sensitivity_level == SensitivityLevel.CRITICAL:
            return PolicyDecision.DEFER_HUMAN_REVIEW, "Critical sensitivity detected"
        
        return PolicyDecision.ALLOW, None
    
    async def _assess_sensitivity(
        self,
        message: Dict[str, Any],
        annotations: Optional[MessageAnnotations] = None
    ) -> SensitivityLevel:
        """Assess the sensitivity level of a message"""
        if not message.get('text_content'):
            return SensitivityLevel.SAFE
            
        text_lower = message['text_content'].lower()
        
        # Only critical keywords (immediate human review)
        critical_keywords = [
            "suicide", "kill myself", "end my life", "want to die",
            "emergency", "urgent help", "police", "lawyer", "legal action"
        ]
        
        if any(keyword in text_lower for keyword in critical_keywords):
            return SensitivityLevel.CRITICAL
        
        return SensitivityLevel.SAFE
    
    async def get_reply_constraints(
        self,
        contact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get constraints for reply generation based on current state"""
        constraints = {
            "max_length": 150,  # Default max length in words
            "tone_adjustment": None,
            "content_restrictions": [],
            "suggested_delay_seconds": 0  # No delays
        }
        
        # Adjust based on progression stage
        stage = contact.get('progression_stage', 'discovery')
        
        if stage == "discovery":
            constraints["tone_adjustment"] = "curious and friendly"
            constraints["content_restrictions"].append("avoid suggesting meetings")
            
        elif stage == "rapport":
            constraints["tone_adjustment"] = "warm and engaging"
            
        elif stage == "logistics_candidate":
            constraints["tone_adjustment"] = "casual and suggestive"
            constraints["content_restrictions"].append("subtle meeting suggestions only")
            
        elif stage in ["proposal", "negotiation"]:
            constraints["tone_adjustment"] = "accommodating and flexible"
            constraints["max_length"] = 100  # Shorter, more focused
            
        elif stage == "confirmation":
            constraints["tone_adjustment"] = "excited and appreciative"
            constraints["content_restrictions"].append("avoid changing plans")
            
        elif stage == "post_confirmation":
            constraints["tone_adjustment"] = "supportive and helpful"
            constraints["content_restrictions"].append("focus on logistics and support")
        
        return constraints 