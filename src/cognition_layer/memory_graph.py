"""
Memory graph management for maintaining contact knowledge
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from src.persistence_layer.supabase_manager import SupabaseManager
from src.persistence_layer.models import Contact, Fact, Message, ProgressionStage
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryGraph:
    """Manages the memory graph for contacts"""
    
    def __init__(self):
        self.db_manager = SupabaseManager()
        
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
        contact = await self.db_manager.get_contact_by_id(contact_id)
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
            category = self._categorize_fact(fact['key'])
            fact_categories[category].append({
                "key": fact['key'],
                "value": fact['value'],
                "confidence": fact['extraction_confidence'],
                "last_reinforced": fact['last_reinforced'],
                "version": fact['version']
            })
        
        # Get unresolved questions or topics
        unresolved = await self._get_unresolved_topics(contact_id)
        
        # Get personality traits
        personality_traits = await self._extract_personality_traits(contact_id)
        
        synopsis = {
            "contact_id": contact_id,
            "contact_name": contact.get('name') or "Unknown",
            "progression_stage": contact.get('progression_stage', 'discovery'),
            "last_interaction": contact.get('last_inbound_message_at'),
            "fact_categories": fact_categories,
            "unresolved_topics": unresolved,
            "personality_traits": personality_traits,
            "engagement_metrics": {
                "response_latency_avg": contact.get('response_latency_avg'),
                "reciprocity_ratio": contact.get('reciprocity_ratio')
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
        for i, message in enumerate(messages):
            if message.get('extracted_entities_json'):
                entities = message['extracted_entities_json']
                # Look for questions that haven't been answered
                if isinstance(entities, dict) and entities.get("questions"):
                    for question in entities["questions"]:
                        # Simple heuristic: if it's in the last 10 messages, consider it unresolved
                        if i < 10:
                            unresolved.append({
                                "question": question,
                                "asked_at": message['timestamp'],
                                "message_id": message['id']
                            })
        
        return unresolved[:5]  # Limit to 5 most recent
    
    async def _extract_personality_traits(self, contact_id: int) -> List[str]:
        """Extract personality traits based on conversation patterns"""
        # Get recent messages with sentiment
        messages = await self.db_manager.get_recent_messages(contact_id, limit=100)
        
        traits = []
        sentiment_counts = {"positive": 0, "negative": 0, "excited": 0, "curious": 0}
        
        for message in messages:
            if message.get('is_inbound') and message.get('sentiment'):
                sentiment = message['sentiment']
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        # Derive traits from patterns
        total_messages = len([m for m in messages if m.get('is_inbound')])
        
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
            if messages[i].get('is_inbound') and not messages[i+1].get('is_inbound'):
                current_time = datetime.fromisoformat(messages[i]['timestamp'])
                next_time = datetime.fromisoformat(messages[i+1]['timestamp'])
                time_diff = next_time - current_time
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
        contact = await self.db_manager.get_contact_by_id(contact_id)
        if not contact:
            return
            
        current_stage = contact.get('progression_stage', 'discovery')
        new_stage = current_stage
        
        # Stage progression logic
        all_fact_keys = [f["key"] for f in new_facts + reinforced_facts]
        
        if current_stage == "discovery":
            # Move to rapport if we've learned personal interests
            if any("interest" in key or "likes" in key for key in all_fact_keys):
                new_stage = "rapport"
                
        elif current_stage == "rapport":
            # Move to logistics candidate if meeting is mentioned
            meeting_keywords = ["meet", "hangout", "date", "coffee", "dinner", "lunch"]
            if any(any(keyword in fact["value"].lower() for keyword in meeting_keywords) 
                   for fact in new_facts + reinforced_facts):
                new_stage = "logistics_candidate"
                
        elif current_stage == "logistics_candidate":
            # Move to proposal if logistics are discussed
            logistics_keywords = ["when", "where", "time", "location", "address"]
            if any(any(keyword in fact["value"].lower() for keyword in logistics_keywords) 
                   for fact in new_facts + reinforced_facts):
                new_stage = "proposal"
                
        elif current_stage == "proposal":
            # Move to negotiation if proposal is made
            proposal_keywords = ["offer", "proposal", "suggest", "recommend"]
            if any(any(keyword in fact["value"].lower() for keyword in proposal_keywords) 
                   for fact in new_facts + reinforced_facts):
                new_stage = "negotiation"
                
        elif current_stage == "negotiation":
            # Move to confirmation if agreement is reached
            agreement_keywords = ["agree", "accept", "yes", "okay", "sounds good"]
            if any(any(keyword in fact["value"].lower() for keyword in agreement_keywords) 
                   for fact in new_facts + reinforced_facts):
                new_stage = "confirmation"
        
        # Update stage if changed
        if new_stage != current_stage:
            await self.db_manager.update_contact_progression_stage(contact_id, new_stage)
            logger.info(f"Contact {contact_id} progressed from {current_stage} to {new_stage}")
    
    async def search_relevant_context(
        self,
        contact_id: int,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for relevant context using semantic similarity"""
        return await self.db_manager.search_similar_messages(
            query_text=query,
            contact_id=contact_id,
            limit=limit,
            threshold=0.6
        )
    
    async def get_fact_by_key(self, contact_id: int, key: str) -> Optional[Dict[str, Any]]:
        """Get a specific fact by key for a contact"""
        facts = await self.db_manager.get_contact_facts(contact_id)
        for fact in facts:
            if fact['key'] == key:
                return fact
        return None
    
    async def update_fact_confidence(
        self,
        fact_id: int,
        new_confidence: float
    ):
        """Update the confidence of a specific fact"""
        try:
            self.db_manager.supabase.table('facts').update({
                'extraction_confidence': new_confidence,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', fact_id).execute()
            logger.info(f"Updated fact confidence: {fact_id} -> {new_confidence}")
        except Exception as e:
            logger.error(f"Error updating fact confidence: {str(e)}")
    
    async def get_contact_timeline(
        self,
        contact_id: int,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """Get a timeline of interactions for a contact"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        try:
            result = self.db_manager.supabase.table('messages').select('*').eq('contact_id', contact_id).gte('timestamp', cutoff_date.isoformat()).order('timestamp', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting contact timeline: {str(e)}")
            return []
    
    async def get_contact_summary(self, contact_id: int) -> Dict[str, Any]:
        """Get a comprehensive summary of contact interactions"""
        contact = await self.db_manager.get_contact_by_id(contact_id)
        if not contact:
            return {}
        
        # Get recent messages
        messages = await self.db_manager.get_recent_messages(contact_id, limit=50)
        
        # Get facts
        facts = await self.db_manager.get_contact_facts(contact_id, limit=20)
        
        # Calculate engagement metrics
        inbound_messages = [m for m in messages if m.get('is_inbound')]
        outbound_messages = [m for m in messages if not m.get('is_inbound')]
        
        summary = {
            "contact_id": contact_id,
            "contact_name": contact.get('name'),
            "progression_stage": contact.get('progression_stage'),
            "total_messages": len(messages),
            "inbound_messages": len(inbound_messages),
            "outbound_messages": len(outbound_messages),
            "total_facts": len(facts),
            "last_interaction": contact.get('last_inbound_message_at'),
            "response_latency_avg": contact.get('response_latency_avg'),
            "reciprocity_ratio": contact.get('reciprocity_ratio'),
            "ai_enabled": contact.get('ai_enabled', False)
        }
        
        return summary 