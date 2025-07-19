"""
Memory graph management for maintaining contact knowledge
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from src.persistence_layer.db_manager import DatabaseManager
from src.persistence_layer.models import Contact, Fact, Message, ProgressionStage
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryGraph:
    """Manages the memory graph for contacts"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        
    async def __aenter__(self):
        await self.db_manager.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db_manager.__aexit__(exc_type, exc_val, exc_tb)
    
    async def get_contact_synopsis(
        self, 
        contact_id: int,
        max_facts: int = 20
    ) -> Dict[str, Any]:
        """Generate a comprehensive synopsis of contact knowledge"""
        # Get contact
        async with self.db_manager.async_session() as session:
            contact = await session.get(Contact, contact_id)
            if not contact:
                return {}
        
        # Get facts
        facts = await self.db_manager.get_contact_facts(contact_id, limit=max_facts)
        
        # Organize facts by category
        fact_categories = {
            "interests": [],
            "personal_info": [],
            "preferences": [],
            "boundaries": [],
            "relationships": [],
            "activities": [],
            "timeline": [],
            "other": []
        }
        
        for fact in facts:
            category = self._categorize_fact(fact.key)
            fact_categories[category].append({
                "key": fact.key,
                "value": fact.value,
                "confidence": fact.extraction_confidence,
                "last_reinforced": fact.last_reinforced.isoformat(),
                "version": fact.version
            })
        
        # Get unresolved questions or topics
        unresolved = await self._get_unresolved_topics(contact_id)
        
        # Get personality traits
        personality_traits = await self._extract_personality_traits(contact_id)
        
        synopsis = {
            "contact_id": contact_id,
            "contact_name": contact.name or "Unknown",
            "progression_stage": contact.progression_stage.value,
            "last_interaction": contact.last_inbound_message_at.isoformat() if contact.last_inbound_message_at else None,
            "fact_categories": fact_categories,
            "unresolved_topics": unresolved,
            "personality_traits": personality_traits,
            "engagement_metrics": {
                "response_latency_avg": contact.response_latency_avg,
                "reciprocity_ratio": contact.reciprocity_ratio
            }
        }
        
        return synopsis
    
    def _categorize_fact(self, key: str) -> str:
        """Categorize a fact based on its key"""
        key_lower = key.lower()
        
        interest_keywords = ["likes", "enjoys", "interested", "hobby", "passion", "favorite"]
        personal_keywords = ["name", "age", "job", "work", "lives", "from", "birthday"]
        preference_keywords = ["prefers", "wants", "wishes", "hopes", "dreams"]
        boundary_keywords = ["dislikes", "hates", "avoid", "never", "boundary", "limit"]
        relationship_keywords = ["friend", "family", "partner", "ex", "dating"]
        activity_keywords = ["does", "plays", "goes", "visits", "travels"]
        timeline_keywords = ["when", "date", "time", "schedule", "available"]
        
        if any(keyword in key_lower for keyword in interest_keywords):
            return "interests"
        elif any(keyword in key_lower for keyword in personal_keywords):
            return "personal_info"
        elif any(keyword in key_lower for keyword in preference_keywords):
            return "preferences"
        elif any(keyword in key_lower for keyword in boundary_keywords):
            return "boundaries"
        elif any(keyword in key_lower for keyword in relationship_keywords):
            return "relationships"
        elif any(keyword in key_lower for keyword in activity_keywords):
            return "activities"
        elif any(keyword in key_lower for keyword in timeline_keywords):
            return "timeline"
        else:
            return "other"
    
    async def _get_unresolved_topics(self, contact_id: int) -> List[Dict[str, Any]]:
        """Extract unresolved questions or topics from recent conversations"""
        # Get recent messages
        messages = await self.db_manager.get_recent_messages(contact_id, limit=50)
        
        unresolved = []
        for message in messages:
            if message.extracted_entities_json:
                entities = message.extracted_entities_json
                # Look for questions that haven't been answered
                if isinstance(entities, dict) and entities.get("questions"):
                    for question in entities["questions"]:
                        # Simple heuristic: if it's in the last 10 messages, consider it unresolved
                        if messages.index(message) < 10:
                            unresolved.append({
                                "question": question,
                                "asked_at": message.timestamp.isoformat(),
                                "message_id": message.id
                            })
        
        return unresolved[:5]  # Limit to 5 most recent
    
    async def _extract_personality_traits(self, contact_id: int) -> List[str]:
        """Extract personality traits based on conversation patterns"""
        # Get recent messages with sentiment
        messages = await self.db_manager.get_recent_messages(contact_id, limit=100)
        
        traits = []
        sentiment_counts = {"positive": 0, "negative": 0, "excited": 0, "curious": 0}
        
        for message in messages:
            if message.is_inbound and message.sentiment:
                sentiment_counts[message.sentiment] = sentiment_counts.get(message.sentiment, 0) + 1
        
        # Derive traits from patterns
        total_messages = len([m for m in messages if m.is_inbound])
        
        if total_messages > 0:
            if sentiment_counts["positive"] / total_messages > 0.6:
                traits.append("Generally positive")
            if sentiment_counts["excited"] / total_messages > 0.3:
                traits.append("Enthusiastic")
            if sentiment_counts["curious"] / total_messages > 0.2:
                traits.append("Inquisitive")
                
        # Look for response patterns
        quick_responses = 0
        for i in range(len(messages) - 1):
            if messages[i].is_inbound and not messages[i+1].is_inbound:
                time_diff = messages[i+1].timestamp - messages[i].timestamp
                if time_diff < timedelta(minutes=5):
                    quick_responses += 1
                    
        if quick_responses > 5:
            traits.append("Responsive")
            
        return traits
    
    async def update_memory_from_message(
        self,
        contact_id: int,
        message_id: int,
        llm_extraction: Dict[str, Any]
    ):
        """Update memory graph based on new message and LLM extraction"""
        # Parse LLM extraction results
        new_facts = llm_extraction.get("new_facts", [])
        reinforced_facts = llm_extraction.get("reinforced_facts", [])
        conflicts = llm_extraction.get("conflicts_updates", [])
        
        # Update facts in database
        await self.db_manager.update_contact_facts(
            contact_id=contact_id,
            new_facts=new_facts,
            reinforced_facts=reinforced_facts,
            conflicted_facts=conflicts,
            origin_message_id=message_id
        )
        
        # Update progression stage if needed
        await self._update_progression_stage(contact_id, new_facts, reinforced_facts)
        
        logger.info(f"Memory updated for contact {contact_id}", extra={
            "new_facts": len(new_facts),
            "reinforced": len(reinforced_facts),
            "conflicts": len(conflicts)
        })
    
    async def _update_progression_stage(
        self,
        contact_id: int,
        new_facts: List[Dict[str, Any]],
        reinforced_facts: List[Dict[str, Any]]
    ):
        """Update contact progression stage based on conversation evolution"""
        async with self.db_manager.async_session() as session:
            contact = await session.get(Contact, contact_id)
            if not contact:
                return
                
            current_stage = contact.progression_stage
            new_stage = current_stage
            
            # Stage progression logic
            all_fact_keys = [f["key"] for f in new_facts + reinforced_facts]
            
            if current_stage == ProgressionStage.DISCOVERY:
                # Move to rapport if we've learned personal interests
                if any("interest" in key or "likes" in key for key in all_fact_keys):
                    new_stage = ProgressionStage.RAPPORT
                    
            elif current_stage == ProgressionStage.RAPPORT:
                # Move to logistics candidate if meeting is mentioned
                meeting_keywords = ["meet", "hangout", "date", "coffee", "dinner", "lunch"]
                if any(any(kw in fact.get("value", "").lower() for kw in meeting_keywords) 
                      for fact in new_facts):
                    new_stage = ProgressionStage.LOGISTICS_CANDIDATE
                    
            elif current_stage == ProgressionStage.LOGISTICS_CANDIDATE:
                # Move to proposal if specific plans are discussed
                planning_keywords = ["when", "where", "what time", "which day"]
                if any(any(kw in fact.get("value", "").lower() for kw in planning_keywords) 
                      for fact in new_facts):
                    new_stage = ProgressionStage.PROPOSAL
                    
            elif current_stage == ProgressionStage.PROPOSAL:
                # Move to negotiation if there's back-and-forth
                if len(new_facts) > 0 and any("maybe" in f.get("value", "").lower() or 
                                            "how about" in f.get("value", "").lower() 
                                            for f in new_facts):
                    new_stage = ProgressionStage.NEGOTIATION
                    
            elif current_stage == ProgressionStage.NEGOTIATION:
                # Move to confirmation if agreement is reached
                confirmation_keywords = ["yes", "sure", "confirmed", "agreed", "perfect", "works for me"]
                if any(any(kw in fact.get("value", "").lower() for kw in confirmation_keywords) 
                      for fact in new_facts):
                    new_stage = ProgressionStage.CONFIRMATION
            
            # Update if changed
            if new_stage != current_stage:
                contact.progression_stage = new_stage
                await session.commit()
                
                logger.info(f"Progression stage updated", extra={
                    "contact_id": contact_id,
                    "old_stage": current_stage.value,
                    "new_stage": new_stage.value
                })
    
    async def search_relevant_context(
        self,
        contact_id: int,
        query: str,
        limit: int = 5
    ) -> List[Message]:
        """Search for relevant past messages using semantic similarity"""
        return await self.db_manager.search_similar_messages(
            query_text=query,
            contact_id=contact_id,
            limit=limit
        ) 