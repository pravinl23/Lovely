"""
Cognitive orchestrator that coordinates all cognition layer components
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import random
import re

from src.cognition_layer.memory_graph import MemoryGraph
from src.cognition_layer.policy_gate import PolicyGate, PolicyDecision
from src.cognition_layer.reply_generator import ReplyGenerator
from src.cognition_layer.briefing_generator import BriefingGenerator
from src.persistence_layer.db_manager import DatabaseManager
from src.persistence_layer.models import Contact, Message, ProgressionStage, User
from src.api_control_plane.whatsapp_client import WhatsAppClient, TokenExpiredError
from src.core.message_queue import QueueMessage
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


class CognitiveOrchestrator:
    """Orchestrates cognitive processing of messages"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.memory_graph = MemoryGraph()
        self.policy_gate = PolicyGate()
        self.reply_generator = ReplyGenerator()
        self.briefing_generator = BriefingGenerator()
        self.whatsapp_client = WhatsAppClient()
        
        # Track active conversations to prevent duplicate processing
        self._active_conversations = set()
        
    async def __aenter__(self):
        await self.db_manager.__aenter__()
        await self.memory_graph.__aenter__()
        await self.policy_gate.__aenter__()
        await self.reply_generator.__aenter__()
        await self.briefing_generator.__aenter__()
        await self.whatsapp_client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db_manager.__aexit__(exc_type, exc_val, exc_tb)
        await self.memory_graph.__aexit__(exc_type, exc_val, exc_tb)
        await self.policy_gate.__aexit__(exc_type, exc_val, exc_tb)
        await self.reply_generator.__aexit__(exc_type, exc_val, exc_tb)
        await self.briefing_generator.__aexit__(exc_type, exc_val, exc_tb)
        await self.whatsapp_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def process_cognitive_task(self, queue_message: QueueMessage):
        """Main entry point for cognitive processing"""
        data = queue_message.data
        conversation_id = data.get("conversation_id")
        
        # Prevent duplicate processing
        if conversation_id in self._active_conversations:
            logger.warning(f"Conversation {conversation_id} already being processed")
            return
            
        self._active_conversations.add(conversation_id)
        
        try:
            trigger = data.get("trigger")
            
            if trigger == "new_message":
                await self._process_new_message(data)
            elif trigger == "scheduled_check":
                await self._process_scheduled_check(data)
            else:
                logger.warning(f"Unknown trigger type: {trigger}")
                
        except Exception as e:
            logger.error(f"Error in cognitive processing: {str(e)}", exc_info=True)
            
        finally:
            self._active_conversations.discard(conversation_id)
    
    async def _process_new_message(self, data: Dict[str, Any]):
        """Process a new incoming message"""
        message_id = data.get("message_id")
        conversation_id = data.get("conversation_id")
        
        # Small delay to ensure database transaction has committed
        await asyncio.sleep(0.5)
        
        # Get message from database
        async with self.db_manager.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Message).where(Message.whatsapp_message_id == message_id)
            )
            message = result.scalar_one_or_none()
            if not message:
                logger.error(f"Message not found: {message_id}")
                return
            
            contact = await session.get(Contact, message.contact_id)
            if not contact:
                logger.error(f"Contact not found for message: {message_id}")
                return
            
            from src.persistence_layer.models import User
            user = await session.get(User, contact.user_id)
            if not user:
                logger.error(f"User not found for contact: {contact.id}")
                return
        
        # Update memory graph with fact extraction
        await self._update_memory(contact.id, message)
        
        # Check policy for reply permission
        # Reconstruct annotations from database fields
        from src.perception_layer.models import MessageAnnotations, Sentiment, Intent
        annotations = None
        if message.sentiment or message.extracted_intents_json or message.extracted_entities_json:
            annotations = MessageAnnotations()
            
            # Reconstruct sentiment
            if message.sentiment:
                try:
                    annotations.sentiment = Sentiment(message.sentiment)
                except ValueError:
                    annotations.sentiment = Sentiment.NEUTRAL
            
            # Reconstruct intents
            if message.extracted_intents_json:
                for intent_str in message.extracted_intents_json:
                    try:
                        annotations.intents.append(Intent(intent_str))
                    except ValueError:
                        pass
        
        decision, reason = await self.policy_gate.evaluate_reply_permission(
            contact_id=contact.id,
            message=message,
            annotations=annotations
        )
        
        if decision == PolicyDecision.ALLOW:
            # Get reply constraints
            constraints = await self.policy_gate.get_reply_constraints(contact)
            
            # Apply delay if suggested
            if constraints.get("suggested_delay_seconds", 0) > 0:
                await asyncio.sleep(constraints["suggested_delay_seconds"])
            
            # Generate and send reply
            await self._generate_and_send_reply(contact, message, constraints)
            
        elif decision == PolicyDecision.DEFER_HUMAN_REVIEW:
            # Just log for now - no email notifications
            logger.info(f"Message requires human review for contact {contact.id}: {reason}")
            
        else:
            logger.info(f"Reply blocked for contact {contact.id}: {reason}")
        
        # Check for stage transitions
        await self._check_stage_transitions(contact, message)
    
    async def _update_memory(self, contact_id: int, message: Message):
        """Update memory graph from new message"""
        # Use LLM to extract fact deltas
        llm_extraction = await self._extract_facts_from_message(contact_id, message)
        
        # Update memory graph
        await self.memory_graph.update_memory_from_message(
            contact_id=contact_id,
            message_id=message.id,
            llm_extraction=llm_extraction
        )
    
    async def _extract_facts_from_message(
        self, 
        contact_id: int, 
        message: Message
    ) -> Dict[str, Any]:
        """Extract facts using LLM"""
        if not message.text_content:
            return {"new_facts": [], "reinforced_facts": [], "conflicts_updates": []}
        
        # Get existing facts for context
        facts = await self.db_manager.get_contact_facts(contact_id, limit=20)
        existing_facts_text = "\n".join([
            f"- {fact.key}: {fact.value}" for fact in facts
        ])
        
        prompt = f"""You are updating a knowledge base about a person based on a new WhatsApp message.

Current known facts about the person:
{existing_facts_text if existing_facts_text else "No existing facts"}

New WhatsApp message: "{message.text_content}"

Based on the new message:
1. **New Assertions:** Identify any new facts about the person. Format as JSON: {{"key": "fact_type", "value": "fact_value"}}
2. **Reinforcements:** Which existing facts are confirmed? List just the keys.
3. **Conflicts/Updates:** If any existing facts are contradicted, provide: {{"key": "fact_key", "old_value": "old", "new_value": "new"}}

Provide output in JSON format with keys: new_facts, reinforced_facts, conflicts_updates"""

        # Call LLM (simplified - would use proper LLM integration)
        if settings.llm_provider == "openai":
            # Would call OpenAI here
            pass
        
        # For now, return empty extraction
        return {
            "new_facts": [],
            "reinforced_facts": [],
            "conflicts_updates": []
        }
    
    async def _generate_and_send_reply(
        self,
        contact: Contact,
        message: Message,
        constraints: Dict[str, Any]
    ):
        """Generate and send a reply"""
        try:
            # Generate reply
            reply_text, meta_tags = await self.reply_generator.generate_reply(
                contact_id=contact.id,
                message_id=message.id,
                constraints=constraints
            )
            
            # Parse multiple messages from the reply
            messages_to_send = await self._parse_multiple_messages(reply_text)
            
            sent_message_ids = []
            
            # Send each message separately with delays
            for i, msg_text in enumerate(messages_to_send):
                if i > 0:
                    # Add delay between messages (1-3 seconds)
                    delay = random.uniform(1.0, 3.0)
                    await asyncio.sleep(delay)
                
                # Send individual message
                result = await self.whatsapp_client.send_whatsapp_message(
                    contact_id=contact.whatsapp_id,
                    message_type="text",
                    content=msg_text
                )
                
                if result and result.get("messages"):
                    sent_message_ids.append(result["messages"][0].get("id"))
                
                # Store each outbound message
                await self._store_outbound_message(
                    contact=contact,
                    reply_text=msg_text,
                    whatsapp_message_id=result.get("messages", [{}])[0].get("id") if result else None,
                    meta_tags=meta_tags if i == 0 else {}  # Only store meta_tags for first message
                )
            
            # Update contact metrics
            await self.db_manager.update_contact_metrics(
                contact_id=contact.id,
                last_ai_reply_at=datetime.utcnow()
            )
            
            logger.info(f"Multiple replies sent to contact {contact.id}", extra={
                "message_id": message.id,
                "messages_sent": len(messages_to_send),
                "total_length": len(reply_text),
                "meta_tags": meta_tags
            })
            
        except TokenExpiredError as e:
            logger.error("="*80)
            logger.error("🚨 WHATSAPP ACCESS TOKEN EXPIRED")
            logger.error("="*80)
            logger.error("Your WhatsApp access token has expired and needs to be refreshed.")
            logger.error("")
            logger.error("TO FIX THIS:")
            logger.error("1. Go to https://developers.facebook.com/apps/")
            logger.error("2. Select your WhatsApp Business app")
            logger.error("3. Go to WhatsApp > API Setup")
            logger.error("4. Generate a new temporary access token")
            logger.error("5. Update WHATSAPP_ACCESS_TOKEN in your .env file")
            logger.error("6. Restart the application")
            logger.error("")
            logger.error("NOTE: Temporary tokens expire after 24 hours.")
            logger.error("For production, set up a permanent token using System User tokens.")
            logger.error("="*80)
                
        except Exception as e:
            logger.error(f"Failed to generate/send reply: {str(e)}", exc_info=True)
    
    async def _parse_multiple_messages(self, reply_text: str) -> List[str]:
        """Parse reply text to extract multiple messages"""
        try:
            # Try to parse as JSON first
            import json
            data = json.loads(reply_text)
            messages = data.get("messages", [])
            if messages:
                return [msg.strip() for msg in messages if msg.strip()]
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # Fallback: split by newlines or sentences if it's a regular text response
        if '\n' in reply_text:
            # Split by newlines
            messages = [msg.strip() for msg in reply_text.split('\n') if msg.strip()]
        else:
            # Single message or split by sentences
            import re
            sentences = re.split(r'(?<=[.!?])\s+', reply_text.strip())
            if len(sentences) > 1 and len(sentences) <= 3:
                messages = [s.strip() for s in sentences if s.strip()]
            else:
                messages = [reply_text.strip()]
        
        # Ensure we don't send too many messages
        return messages[:3] if messages else [reply_text.strip()]
    
    async def _store_outbound_message(
        self,
        contact: Contact,
        reply_text: str,
        whatsapp_message_id: str,
        meta_tags: Dict[str, Any]
    ):
        """Store outbound message in database"""
        from src.perception_layer.models import Message as PerceptionMessage
        
        # Create message record
        message = PerceptionMessage(
            message_id=whatsapp_message_id,
            conversation_id=contact.whatsapp_id,
            sender_id=contact.user_id,  # Our system
            receiver_id=contact.whatsapp_id,
            timestamp=datetime.utcnow(),
            text_content=reply_text,
            is_inbound=False
        )
        
        # Store in database
        await self.db_manager.store_message(message)
        
        # Update reply status
        # Would update OutboundReply status to "sent" here
    
    async def _check_stage_transitions(self, contact: Contact, message: Message):
        """Check for stage transitions and trigger actions"""
        # Get updated contact with latest stage
        async with self.db_manager.async_session() as session:
            contact = await session.get(Contact, contact.id)
            
            # Just log stage transitions for now - no email briefings
            if contact.progression_stage == ProgressionStage.CONFIRMATION:
                logger.info(f"Contact {contact.id} reached confirmation stage")
    
    async def _get_recent_briefings(self, contact_id: int) -> List[Any]:
        """Get recent briefings for a contact"""
        # Would query Briefing table
        return []
    
    async def _process_scheduled_check(self, data: Dict[str, Any]):
        """Process scheduled check for follow-ups"""
        contact_id = data.get("contact_id")
        
        # Get contact
        async with self.db_manager.async_session() as session:
            contact = await session.get(Contact, contact_id)
            if not contact or not contact.ai_enabled:
                return
        
        # Check if follow-up is appropriate
        if not await self._should_send_followup(contact):
            return
        
        # Generate a follow-up message
        # This would be more sophisticated in production
        logger.info(f"Scheduled check for contact {contact_id} - no action taken")
    
    async def _should_send_followup(self, contact: Contact) -> bool:
        """Determine if a follow-up message is appropriate"""
        if not contact.last_inbound_message_at:
            return False
            
        # Don't follow up if recent activity
        time_since_last = datetime.utcnow() - contact.last_inbound_message_at
        if time_since_last < timedelta(hours=12):
            return False
            
        # Don't follow up outside 24h window
        if time_since_last > timedelta(hours=24):
            return False
            
        # Check stage-specific rules
        if contact.progression_stage in [ProgressionStage.NEGOTIATION, ProgressionStage.CONFIRMATION]:
            # More careful in sensitive stages
            return False
            
        return True 