"""
Briefing generator for creating comprehensive date confirmation briefings
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from src.cognition_layer.memory_graph import MemoryGraph
from src.persistence_layer.db_manager import DatabaseManager
from src.persistence_layer.models import Contact, Message, Fact
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


class BriefingGenerator:
    """Generates comprehensive briefings for confirmed dates"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.memory_graph = MemoryGraph()
        self.httpx_client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        await self.db_manager.__aenter__()
        await self.memory_graph.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db_manager.__aexit__(exc_type, exc_val, exc_tb)
        await self.httpx_client.aclose()
    
    async def generate_date_briefing(self, contact_id: int) -> Dict[str, Any]:
        """Generate a comprehensive briefing for a confirmed date"""
        # Get contact
        async with self.db_manager.async_session() as session:
            contact = await session.get(Contact, contact_id)
            if not contact:
                raise ValueError(f"Contact not found: {contact_id}")
        
        # Get memory synopsis
        memory_synopsis = await self.memory_graph.get_contact_synopsis(contact_id)
        
        # Get recent conversation
        recent_messages = await self.db_manager.get_recent_messages(
            contact_id=contact_id,
            limit=50
        )
        
        # Extract date details from recent conversation
        date_details = await self._extract_date_details(recent_messages)
        
        # Calculate engagement metrics
        engagement_metrics = await self._calculate_engagement_metrics(contact, recent_messages)
        
        # Extract key interests
        key_interests = self._extract_key_interests(memory_synopsis)
        
        # Identify green flags and boundaries
        green_flags = await self._identify_green_flags(memory_synopsis, recent_messages)
        boundaries = self._extract_boundaries(memory_synopsis)
        
        # Get promised follow-ups
        promised_followups = await self._extract_promised_followups(recent_messages)
        
        # Generate conversation starters and callbacks
        conversation_starters = await self._generate_conversation_starters(memory_synopsis)
        continuity_callbacks = await self._generate_continuity_callbacks(memory_synopsis)
        
        # Generate summary using LLM
        summary = await self._generate_summary(contact, memory_synopsis, recent_messages)
        
        briefing_data = {
            "contact_name": contact.name or "Your match",
            "summary_paragraph": summary,
            "date_details": date_details,
            "engagement_metrics": engagement_metrics,
            "key_interests": key_interests,
            "green_flags": green_flags,
            "boundaries_caution_notes": boundaries,
            "promised_follow_ups": promised_followups,
            "conversation_openers": conversation_starters,
            "continuity_callbacks": continuity_callbacks
        }
        
        return briefing_data
    
    async def _extract_date_details(self, messages: List[Message]) -> Dict[str, Any]:
        """Extract confirmed date details from recent messages"""
        # Look for date-related entities in recent messages
        date_info = {
            "activity": None,
            "time_normalized_utc": None,
            "time_formatted": None,
            "location": None,
            "explicitly_fixed": False
        }
        
        # Reverse order to find most recent confirmations
        for msg in reversed(messages[-20:]):  # Focus on last 20 messages
            if msg.extracted_entities_json:
                entities = msg.extracted_entities_json
                
                # Look for activity mentions
                if not date_info["activity"]:
                    for entity in entities:
                        if entity.get("type") == "event":
                            date_info["activity"] = entity.get("value")
                
                # Look for time mentions
                if not date_info["time_normalized_utc"]:
                    for entity in entities:
                        if entity.get("type") in ["date", "time"]:
                            # Would need proper date parsing here
                            date_info["time_formatted"] = entity.get("value")
                
                # Look for location mentions
                if not date_info["location"]:
                    for entity in entities:
                        if entity.get("type") == "location":
                            date_info["location"] = entity.get("value")
        
        # Set defaults if not found
        if not date_info["activity"]:
            date_info["activity"] = "Meeting up"
        if not date_info["time_formatted"]:
            date_info["time_formatted"] = "To be confirmed"
        if not date_info["location"]:
            date_info["location"] = "To be decided"
        
        return date_info
    
    async def _calculate_engagement_metrics(
        self, 
        contact: Contact, 
        messages: List[Message]
    ) -> Dict[str, Any]:
        """Calculate engagement metrics"""
        metrics = {
            "response_time": "N/A",
            "message_count": len(messages),
            "positive_sentiment": 0
        }
        
        # Format response time
        if contact.response_latency_avg:
            if contact.response_latency_avg < 60:
                metrics["response_time"] = f"{int(contact.response_latency_avg)} seconds"
            elif contact.response_latency_avg < 3600:
                metrics["response_time"] = f"{int(contact.response_latency_avg / 60)} minutes"
            else:
                metrics["response_time"] = f"{int(contact.response_latency_avg / 3600)} hours"
        
        # Calculate positive sentiment percentage
        positive_count = sum(
            1 for msg in messages 
            if msg.is_inbound and msg.sentiment in ["positive", "excited", "warm"]
        )
        inbound_count = sum(1 for msg in messages if msg.is_inbound)
        
        if inbound_count > 0:
            metrics["positive_sentiment"] = int((positive_count / inbound_count) * 100)
        
        return metrics
    
    def _extract_key_interests(self, synopsis: Dict[str, Any]) -> List[str]:
        """Extract key interests from memory synopsis"""
        interests = []
        
        interest_facts = synopsis.get("fact_categories", {}).get("interests", [])
        for fact in interest_facts[:5]:  # Top 5 interests
            interests.append(fact["value"])
        
        # Also add from activities
        activity_facts = synopsis.get("fact_categories", {}).get("activities", [])
        for fact in activity_facts[:2]:
            if fact["value"] not in interests:
                interests.append(fact["value"])
        
        return interests
    
    async def _identify_green_flags(
        self, 
        synopsis: Dict[str, Any], 
        messages: List[Message]
    ) -> List[str]:
        """Identify positive indicators"""
        green_flags = []
        
        # From personality traits
        traits = synopsis.get("personality_traits", [])
        positive_traits = ["Enthusiastic", "Responsive", "Generally positive"]
        for trait in traits:
            if trait in positive_traits:
                green_flags.append(trait)
        
        # From conversation patterns
        # Check for questions asked (shows interest)
        question_count = sum(
            1 for msg in messages[-20:] 
            if msg.is_inbound and msg.extracted_entities_json 
            and msg.extracted_entities_json.get("questions")
        )
        
        if question_count > 3:
            green_flags.append("Shows genuine curiosity by asking questions")
        
        # Check for shared interests
        shared_interests = synopsis.get("fact_categories", {}).get("interests", [])
        if len(shared_interests) > 2:
            green_flags.append(f"Shares multiple interests including {shared_interests[0]['value']}")
        
        return green_flags[:5]  # Limit to 5
    
    def _extract_boundaries(self, synopsis: Dict[str, Any]) -> List[str]:
        """Extract boundaries and caution notes"""
        boundaries = []
        
        boundary_facts = synopsis.get("fact_categories", {}).get("boundaries", [])
        for fact in boundary_facts:
            boundaries.append(f"{fact['key']}: {fact['value']}")
        
        return boundaries
    
    async def _extract_promised_followups(self, messages: List[Message]) -> List[str]:
        """Extract any promises made by the AI"""
        followups = []
        
        # Look for outbound messages with promise-like language
        promise_keywords = ["i'll send", "i'll share", "i'll tell you", "remind me to"]
        
        for msg in messages:
            if not msg.is_inbound and msg.text_content:
                text_lower = msg.text_content.lower()
                for keyword in promise_keywords:
                    if keyword in text_lower:
                        # Extract the promise context
                        followups.append(msg.text_content)
                        break
        
        return followups[:3]  # Limit to 3
    
    async def _generate_conversation_starters(
        self, 
        synopsis: Dict[str, Any]
    ) -> List[str]:
        """Generate conversation starter suggestions"""
        starters = []
        
        # Based on interests
        interests = synopsis.get("fact_categories", {}).get("interests", [])
        if interests:
            starters.append(f"How's your {interests[0]['value']} going?")
        
        # Based on unresolved topics
        unresolved = synopsis.get("unresolved_topics", [])
        if unresolved:
            starters.append(f"You mentioned {unresolved[0]['question']} - I'm curious about that")
        
        # Generic but personalized
        starters.append("I've been thinking about what you said earlier...")
        
        return starters[:3]
    
    async def _generate_continuity_callbacks(
        self, 
        synopsis: Dict[str, Any]
    ) -> List[str]:
        """Generate topics to follow up on"""
        callbacks = []
        
        # From personal info
        personal_facts = synopsis.get("fact_categories", {}).get("personal_info", [])
        for fact in personal_facts[:2]:
            if fact["key"] in ["job", "work"]:
                callbacks.append(f"Ask about their work in {fact['value']}")
            elif fact["key"] == "from":
                callbacks.append(f"Ask about growing up in {fact['value']}")
        
        # From timeline events
        timeline_facts = synopsis.get("fact_categories", {}).get("timeline", [])
        for fact in timeline_facts[:1]:
            callbacks.append(f"Follow up on: {fact['value']}")
        
        # From activities
        activity_facts = synopsis.get("fact_categories", {}).get("activities", [])
        if activity_facts:
            callbacks.append(f"Ask about their recent {activity_facts[0]['value']}")
        
        return callbacks[:4]
    
    async def _generate_summary(
        self,
        contact: Contact,
        synopsis: Dict[str, Any],
        messages: List[Message]
    ) -> str:
        """Generate a warm summary paragraph using LLM"""
        # Build context for LLM
        interests = ", ".join([f["value"] for f in synopsis.get("fact_categories", {}).get("interests", [])[:3]])
        traits = ", ".join(synopsis.get("personality_traits", []))
        
        prompt = f"""Generate a warm, friendly 2-3 sentence summary of this person for someone about to go on a date with them.

Name: {contact.name or "They"}
Key interests: {interests}
Personality: {traits}
Conversation stage: {contact.progression_stage.value}

The summary should be positive, highlight what makes them interesting, and create anticipation for the date.
Keep it concise and personal."""

        # For now, return a template summary
        summary = f"{contact.name or 'They'} seems like a {traits.lower() if traits else 'lovely'} person"
        
        if interests:
            summary += f" with a passion for {interests}"
        
        summary += ". The conversation has been flowing naturally and there's definitely a good connection building."
        
        return summary 