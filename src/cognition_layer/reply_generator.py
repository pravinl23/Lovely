"""
Reply generator using LLMs for contextual response generation
"""
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import httpx
import asyncio
import random

from src.cognition_layer.memory_graph import MemoryGraph
from src.persistence_layer.supabase_manager import SupabaseManager
from src.persistence_layer.models import Contact, Message, OutboundReply, ProgressionStage
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


class ReplyGenerator:
    """Generates contextual replies using LLMs"""
    
    def __init__(self):
        self.db_manager = SupabaseManager()
        self.memory_graph = MemoryGraph()
        self.httpx_client = httpx.AsyncClient(timeout=60.0)
        
    async def __aenter__(self):
        await self.db_manager.__aenter__()
        await self.memory_graph.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db_manager.__aexit__(exc_type, exc_val, exc_tb)
        await self.memory_graph.__aexit__(exc_type, exc_val, exc_tb)
        await self.httpx_client.aclose()
    
    async def generate_reply(
        self,
        contact_id: int,
        message_id: int,
        constraints: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate a reply for a message"""
        # Get contact and message
        contact = await self.db_manager.get_contact_by_id(contact_id)
        message = await self.db_manager.get_message_by_id(message_id)
        
        if not contact or not message:
            raise ValueError("Contact or message not found")
        
        # Get user persona
        persona = await self._get_user_persona(contact['user_id'])
        
        # Get conversation context
        context = await self._build_conversation_context(contact, message)
        
        # Get memory synopsis
        memory_synopsis = await self.memory_graph.get_contact_synopsis(contact_id)
        
        # Generate reply
        prompt = self._build_reply_prompt(
            persona=persona,
            context=context,
            memory_synopsis=memory_synopsis,
            constraints=constraints,
            contact=contact,
            current_message=message
        )
        
        # Call LLM
        llm_response = await self._call_llm_for_reply(prompt)
        
        # Parse and post-process
        reply_text, meta_tags = self._parse_llm_response(llm_response)
        reply_text = await self._post_process_reply(reply_text, contact, constraints)
        
        # Store the generated reply
        await self._store_outbound_reply(
            message_id=message_id,
            contact_id=contact_id,
            user_id=contact['user_id'],
            reply_text=reply_text,
            prompt_context=self._redact_prompt_context(prompt),
            meta_tags=meta_tags
        )
        
        return reply_text, meta_tags
    
    async def _get_user_persona(self, user_id: int) -> Dict[str, Any]:
        """Extract user's conversational persona from past messages"""
        # Get user's past outbound messages
        user = await self.db_manager.get_user_by_id(user_id)
        if not user or not user.get('persona_profile_json'):
            # Build from scratch
            return await self._analyze_user_persona(user_id)
        return user['persona_profile_json']
    
    async def _analyze_user_persona(self, user_id: int) -> Dict[str, Any]:
        """Analyze user's writing style from past messages"""
        # Get sample of user's messages
        recent_messages = await self.db_manager.get_user_outbound_messages(
            user_id=user_id,
            limit=100
        )
        
        if not recent_messages:
            # Default persona
            return {
                "tone_adjectives": ["friendly", "casual"],
                "emoji_frequency": {"": 0.1, "": 0.05},
                "message_length_quartiles": {"25": 10, "50": 20, "75": 40},
                "common_phrases": [],
                "punctuation_style": "normal"
            }
        
        # Analyze messages
        emoji_counts = {}
        message_lengths = []
        
        for msg in recent_messages:
            if msg.get('text_content'):
                # Count emojis
                emojis = re.findall(r'[\U0001F300-\U0001F9FF]+', msg['text_content'])
                for emoji in emojis:
                    emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1
                
                # Track length
                message_lengths.append(len(msg['text_content'].split()))
        
        # Calculate emoji frequencies
        total_messages = len(recent_messages)
        emoji_frequency = {
            emoji: count / total_messages 
            for emoji, count in sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
        # Calculate length quartiles
        message_lengths.sort()
        quartiles = {
            "25": message_lengths[int(len(message_lengths) * 0.25)] if message_lengths else 10,
            "50": message_lengths[int(len(message_lengths) * 0.50)] if message_lengths else 20,
            "75": message_lengths[int(len(message_lengths) * 0.75)] if message_lengths else 40
        }
        
        return {
            "tone_adjectives": ["friendly", "conversational"],  # Would need LLM analysis for better extraction
            "emoji_frequency": emoji_frequency,
            "message_length_quartiles": quartiles,
            "common_phrases": [],  # Would need more sophisticated analysis
            "punctuation_style": "normal"
        }
    
    async def _build_conversation_context(
        self,
        contact: Dict[str, Any],
        current_message: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build conversation context from recent messages"""
        # Get recent conversation
        recent_messages = await self.db_manager.get_recent_messages(
            contact_id=contact['id'],
            limit=settings.max_context_messages
        )
        
        # Format for prompt
        context = []
        for msg in recent_messages:
            context.append({
                "timestamp": msg['timestamp'],
                "sender": "contact" if msg.get('is_inbound') else "user",
                "text": msg.get('text_content') or f"[{msg.get('media_type')} message]",
                "is_current": msg['id'] == current_message['id']
            })
        
        # Add relevant past context from embeddings
        if current_message.get('text_content'):
            similar_messages = await self.memory_graph.search_relevant_context(
                contact_id=contact['id'],
                query=current_message['text_content'],
                limit=3
            )
            
            for msg in similar_messages:
                if msg['id'] not in [m['id'] for m in recent_messages]:
                    context.append({
                        "timestamp": msg['timestamp'],
                        "sender": "contact" if msg.get('is_inbound') else "user",
                        "text": msg.get('text_content') or f"[{msg.get('media_type')} message]",
                        "is_current": False,
                        "is_historical": True
                    })
        
        return context
    
    def _build_reply_prompt(
        self,
        persona: Dict[str, Any],
        context: List[Dict[str, Any]],
        memory_synopsis: Dict[str, Any],
        constraints: Dict[str, Any],
        contact: Dict[str, Any],
        current_message: Dict[str, Any]
    ) -> str:
        """Build the prompt for reply generation"""
        # Format conversation history
        conversation_text = ""
        for msg in context:
            sender = "You" if msg["sender"] == "user" else contact.get('name') or "Them"
            marker = " [CURRENT]" if msg.get("is_current") else ""
            historical = " [FROM EARLIER]" if msg.get("is_historical") else ""
            conversation_text += f"{sender}: {msg['text']}{marker}{historical}\n"
        
        # Format memory synopsis
        memory_text = self._format_memory_synopsis(memory_synopsis)
        
        # Format constraints
        constraints_text = self._format_constraints(constraints)
        
        # Build persona text
        persona_text = f"""Tone: {', '.join(persona.get('tone_adjectives', ['friendly']))}
Emoji usage: {self._format_emoji_usage(persona.get('emoji_frequency', {}))}
Typical message length: {persona.get('message_length_quartiles', {}).get('50', 20)} words"""
        
        # Determine goal based on stage
        goal_text = self._get_stage_goal(contact.get('progression_stage', 'discovery'))
        
        prompt = f"""You are an AI assistant helping to craft WhatsApp messages. You should adopt the following persona:

{persona_text}

Current conversation goal: {goal_text}

What you know about {contact.get('name') or 'this person'}:
{memory_text}

Recent conversation:
{conversation_text}

Constraints:
{constraints_text}

Generate a natural, contextual reply that matches the persona and moves toward the goal. Keep it conversational and authentic.

Reply:"""
        
        return prompt
    
    def _format_memory_synopsis(self, synopsis: Dict[str, Any]) -> str:
        """Format memory synopsis for prompt"""
        if not synopsis:
            return "No previous information available."
        
        formatted = []
        
        # Add basic info
        if synopsis.get('contact_name'):
            formatted.append(f"Name: {synopsis['contact_name']}")
        
        if synopsis.get('progression_stage'):
            formatted.append(f"Relationship stage: {synopsis['progression_stage']}")
        
        # Add fact categories
        fact_categories = synopsis.get('fact_categories', {})
        for category, facts in fact_categories.items():
            if facts:
                formatted.append(f"\n{category.title()}:")
                for fact in facts[:3]:  # Limit to 3 per category
                    formatted.append(f"  • {fact['key']}: {fact['value']}")
        
        # Add personality traits
        traits = synopsis.get('personality_traits', [])
        if traits:
            formatted.append(f"\nPersonality: {', '.join(traits)}")
        
        # Add engagement metrics
        metrics = synopsis.get('engagement_metrics', {})
        if metrics.get('response_latency_avg'):
            formatted.append(f"\nTypical response time: {metrics['response_latency_avg']:.1f} seconds")
        
        return "\n".join(formatted)
    
    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """Format constraints for prompt"""
        formatted = []
        
        if constraints.get('max_length'):
            formatted.append(f"• Maximum length: {constraints['max_length']} words")
        
        if constraints.get('tone_adjustment'):
            formatted.append(f"• Tone: {constraints['tone_adjustment']}")
        
        if constraints.get('content_restrictions'):
            for restriction in constraints['content_restrictions']:
                formatted.append(f"• Avoid: {restriction}")
        
        if constraints.get('suggested_delay_seconds'):
            formatted.append(f"• Suggested delay: {constraints['suggested_delay_seconds']} seconds")
        
        return "\n".join(formatted) if formatted else "No specific constraints."
    
    def _format_emoji_usage(self, emoji_freq: Dict[str, float]) -> str:
        """Format emoji usage for prompt"""
        if not emoji_freq:
            return "minimal"
        
        # Get top 3 emojis
        top_emojis = sorted(emoji_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        return ", ".join([f"{emoji} ({freq:.1%})" for emoji, freq in top_emojis])
    
    def _get_stage_goal(self, stage: str) -> str:
        """Get conversation goal based on progression stage"""
        goals = {
            "discovery": "Learn about their interests and personality",
            "rapport": "Build connection and trust",
            "logistics_candidate": "Gauge interest in meeting up",
            "proposal": "Suggest specific meeting details",
            "negotiation": "Work out logistics and preferences",
            "confirmation": "Confirm plans and details",
            "post_confirmation": "Provide support and follow-up"
        }
        return goals.get(stage, "Maintain friendly conversation")
    
    async def _call_llm_for_reply(self, prompt: str) -> str:
        """Call LLM for reply generation"""
        if settings.llm_provider == "openai":
            return await self._call_openai_for_reply(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
    
    async def _call_openai_for_reply(self, prompt: str) -> str:
        """Call OpenAI API for reply generation"""
        try:
            headers = {
                "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": settings.llm_model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            response = await self.httpx_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return "Thanks for your message! I'll get back to you soon."
                
        except Exception as e:
            logger.error(f"Error calling OpenAI: {str(e)}")
            return "Thanks for your message! I'll get back to you soon."
    
    def _parse_llm_response(self, response: str) -> Tuple[str, Dict[str, Any]]:
        """Parse LLM response and extract metadata"""
        # Clean up response
        reply_text = response.strip()
        
        # Remove any markdown formatting
        reply_text = re.sub(r'\*\*(.*?)\*\*', r'\1', reply_text)
        reply_text = re.sub(r'\*(.*?)\*', r'\1', reply_text)
        
        # Extract metadata
        meta_tags = {
            "length": len(reply_text.split()),
            "has_emoji": bool(re.findall(r'[\U0001F300-\U0001F9FF]+', reply_text)),
            "has_question": "?" in reply_text,
            "has_exclamation": "!" in reply_text,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return reply_text, meta_tags
    
    async def _post_process_reply(
        self,
        reply_text: str,
        contact: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> str:
        """Post-process the generated reply"""
        processed = reply_text
        
        # Check for similarity with recent messages
        recent_messages = await self.db_manager.get_recent_outbound_messages(
            contact_id=contact['id'],
            limit=5
        )
        
        for msg in recent_messages:
            if msg.get('text_content') and self._is_too_similar(processed, msg['text_content']):
                processed = self._add_variation(processed)
                break
        
        # Add hedging if needed
        if constraints.get('tone_adjustment') == 'cautious':
            processed = self._add_hedging(processed)
        
        # Soften commitments if needed
        if constraints.get('content_restrictions') and any('avoid' in r for r in constraints['content_restrictions']):
            processed = self._soften_commitments(processed)
        
        return processed
    
    def _is_too_similar(self, text1: str, text2: str) -> bool:
        """Check if two texts are too similar"""
        # Simple similarity check - could be improved with embeddings
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity > 0.7  # 70% similarity threshold
    
    def _add_variation(self, text: str) -> str:
        """Add variation to avoid repetition"""
        variations = [
            f"Actually, {text.lower()}",
            f"Well, {text.lower()}",
            f"You know, {text.lower()}",
            f"I think {text.lower()}",
            f"Maybe {text.lower()}"
        ]
        return random.choice(variations)
    
    def _add_hedging(self, text: str) -> str:
        """Add hedging to make text more cautious"""
        hedges = ["I think", "Maybe", "Perhaps", "It seems like", "I'm not sure but"]
        if not any(hedge.lower() in text.lower() for hedge in hedges):
            return f"{random.choice(hedges)} {text.lower()}"
        return text
    
    def _soften_commitments(self, text: str) -> str:
        """Soften any strong commitments in the text"""
        # Replace strong commitments with softer alternatives
        replacements = {
            "I will": "I'll try to",
            "I can": "I might be able to",
            "I am": "I think I am",
            "definitely": "probably",
            "absolutely": "likely"
        }
        
        for strong, soft in replacements.items():
            text = text.replace(strong, soft)
        
        return text
    
    async def _store_outbound_reply(
        self,
        message_id: int,
        contact_id: int,
        user_id: int,
        reply_text: str,
        prompt_context: Dict[str, Any],
        meta_tags: Dict[str, Any]
    ):
        """Store the generated reply in database"""
        await self.db_manager.store_outbound_reply(
            message_id=message_id,
            contact_id=contact_id,
            user_id=user_id,
            reply_text=reply_text,
            prompt_context=prompt_context,
            meta_tags=meta_tags
        )
    
    def _redact_prompt_context(self, prompt: str) -> Dict[str, Any]:
        """Redact sensitive information from prompt before storing"""
        # Store a summary instead of full prompt
        return {
            "prompt_length": len(prompt),
            "timestamp": datetime.utcnow().isoformat(),
            "llm_provider": settings.llm_provider,
            "model": settings.llm_model_name
        } 