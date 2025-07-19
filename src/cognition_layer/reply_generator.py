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
from src.persistence_layer.db_manager import DatabaseManager
from src.persistence_layer.models import Contact, Message, OutboundReply, ProgressionStage
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


class ReplyGenerator:
    """Generates contextual replies using LLMs"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
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
        async with self.db_manager.async_session() as session:
            contact = await session.get(Contact, contact_id)
            message = await session.get(Message, message_id)
            
            if not contact or not message:
                raise ValueError("Contact or message not found")
        
        # Get user persona
        persona = await self._get_user_persona(contact.user_id)
        
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
            user_id=contact.user_id,
            reply_text=reply_text,
            prompt_context=self._redact_prompt_context(prompt),
            meta_tags=meta_tags
        )
        
        return reply_text, meta_tags
    
    async def _get_user_persona(self, user_id: int) -> Dict[str, Any]:
        """Extract user's conversational persona from past messages"""
        # Get user's past outbound messages
        user = await self.db_manager.get_user_by_id(user_id)
        if not user or not user.persona_profile_json:
            # Build from scratch
            return await self._analyze_user_persona(user_id)
        return user.persona_profile_json
    
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
                "emoji_frequency": {"😊": 0.1, "😂": 0.05},
                "message_length_quartiles": {"25": 10, "50": 20, "75": 40},
                "common_phrases": [],
                "punctuation_style": "normal"
            }
        
        # Analyze messages
        emoji_counts = {}
        message_lengths = []
        
        for msg in recent_messages:
            if msg.text_content:
                # Count emojis
                emojis = re.findall(r'[\U0001F300-\U0001F9FF]+', msg.text_content)
                for emoji in emojis:
                    emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1
                
                # Track length
                message_lengths.append(len(msg.text_content.split()))
        
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
        contact: Contact,
        current_message: Message
    ) -> List[Dict[str, Any]]:
        """Build conversation context from recent messages"""
        # Get recent conversation
        recent_messages = await self.db_manager.get_recent_messages(
            contact_id=contact.id,
            limit=settings.max_context_messages
        )
        
        # Format for prompt
        context = []
        for msg in recent_messages:
            context.append({
                "timestamp": msg.timestamp.isoformat(),
                "sender": "contact" if msg.is_inbound else "user",
                "text": msg.text_content or f"[{msg.media_type} message]",
                "is_current": msg.id == current_message.id
            })
        
        # Add relevant past context from embeddings
        if current_message.text_content:
            similar_messages = await self.memory_graph.search_relevant_context(
                contact_id=contact.id,
                query=current_message.text_content,
                limit=3
            )
            
            for msg in similar_messages:
                if msg.id not in [m.id for m in recent_messages]:
                    context.append({
                        "timestamp": msg.timestamp.isoformat(),
                        "sender": "contact" if msg.is_inbound else "user",
                        "text": msg.text_content or f"[{msg.media_type} message]",
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
        contact: Contact,
        current_message: Message
    ) -> str:
        """Build the prompt for reply generation"""
        # Format conversation history
        conversation_text = ""
        for msg in context:
            sender = "You" if msg["sender"] == "user" else contact.name or "Them"
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
        goal_text = self._get_stage_goal(contact.progression_stage)
        
        prompt = f"""You are an AI assistant helping to craft WhatsApp messages. You should adopt the following persona:

{persona_text}

Current conversation goal: {goal_text}

What you know about {contact.name or 'this person'}:
{memory_text}

Recent conversation:
{conversation_text}

Reply constraints:
{constraints_text}

Based on the above, craft a natural, conversational reply to the current message. Your reply should:

GOALS:
- Keep the conversation flowing naturally and engagingly
- Build emotional and intellectual connection with the match
- Present the user as authentic, confident, playful, and respectful
- Guide the conversation toward a real-life date (coffee, drinks, walk, etc.)

PERSONALITY:
- Confident, but never arrogant or show-offy
- Emotionally intelligent and attentive to the match's tone and interests
- Playful and witty with a hint of flirty teasing
- Chill, grounded, and relatable — not over-excited or dramatic
- Curious and thoughtful — show genuine interest in the other person

TONE & LANGUAGE RULES:
- Never reintroduce yourself unless prompted or relevant
- Do NOT say things like "Hi again!" or "Just me checking in"
- Limit emojis to 1 every 5 messages max, and only when it fits naturally
- Avoid overusing exclamation marks (occasional use is fine)
- Avoid robotic or repetitive phrasing — vary sentence structure
- Mirror the match's tone and energy (match their use of slang, punctuation, length, etc.)
- Use modern, casual, conversational English — avoid sounding scripted

CONVERSATION TECHNIQUES:
- Ask open-ended questions that reveal personality (e.g., "What's your idea of a perfect Sunday?")
- Reference earlier parts of the conversation to show attentiveness
- Use playful, flirty teasing sparingly and appropriately (e.g., "Wait, are you one of those pineapple-on-pizza people?")
- Occasionally share brief personal anecdotes to build relatability
- Keep messages short to medium in length — no giant paragraphs unless contextually appropriate
- Do not dominate the conversation — always bring it back to the other person
- Keep the replies short and concise (1-2 sentences per reply)

EMOTIONAL CONNECTION:
- Acknowledge and affirm the other person's opinions or feelings
- Be lightly vulnerable when appropriate (e.g., "Honestly, dating apps can feel weird — I just want to find something real.")
- Use casual humor or shared dreams to create connection (e.g., "You seem like someone I could rate strangers' outfits with at a cafe in Paris.")

DATE PROGRESSION:
- If strong rapport is built after 5–8 exchanges, gently introduce the idea of meeting:
  - "Honestly, I feel like we'd vibe even better in person. Want to grab coffee sometime?"
  - "You seem like someone I'd actually enjoy meeting — any interest in a quick drink?"
- Be flexible and low-pressure. If they say no or avoid the question, don't push.
- Revisit the date idea later if conversation remains strong.

AVOID AT ALL COSTS:
- Repeating your name or reintroducing yourself in each message
- Overusing emojis or sounding overly bubbly
- Long-winded, overly formal, or stiff messages
- Bombarding with questions — make it feel like a natural back-and-forth
- Bragging or info-dumping about achievements
- Sexual innuendos or explicit flirting early on
- Over-texting if they don't reply — allow them to lead if they pause

MEMORY RULES:
- Remember key facts the match shares (e.g., job, hobbies, pets, travel, goals) and reference them later.
- If the match mentions something in a past message (like an event or weekend plan), follow up on it later.
- Keep a light "mental profile" of the person's tone, interests, and conversation style to tailor future replies.
- Don't forget the persona you're representing — stay consistent with past info about yourself.

RESPONSE TO DELAYED REPLIES:
- If the match takes a long time to reply, do NOT guilt them or comment too much on it.
- Acknowledge lightly or ignore:  
  - "Hey, good to hear from you again :)"  
- If the match stops replying mid-convo, wait before re-engaging.

TOPIC TRANSITIONS:
- Use light pivots when a topic gets stale:
  - "That's wild haha. Random question though — what's your go-to comfort movie?"
- Avoid abrupt subject changes unless the previous thread is clearly dead.
- Don't panic if there's a pause or dry moment — a smooth topic shift is better than trying to force energy.

ENERGY MATCHING:
- If the match is high-energy, witty, or sarcastic — match that tone.
- If they're quieter or more serious — lean into curiosity and emotional depth instead of banter.
- You don't have to mirror 100% — just enough to build rapport while gently leading into your own natural style.

HUMAN-LIKE BEHAVIOR:
- Occasionally use natural imperfections (e.g., light typos, rephrasing thoughts) to sound human.
- Do not over-optimize for being clever — occasional simplicity is more believable.
- Use contractions and filler phrases sparingly (e.g., "I mean…", "to be honest", "lowkey").

MULTIPLE MESSAGE INSTRUCTIONS:
- Sometimes split your response into multiple separate messages like real people do
- If you have multiple thoughts, reactions, or questions, send them as separate messages
- Examples of when to split:
  * "That's amazing!" + "How did you get into that?"
  * "Haha I love that" + "Wait, you're not from here originally?"
  * "Coffee sounds perfect" + "I know this great spot downtown"
- Generally send 1-3 messages (rarely more than 3)
- Each message should be a complete thought (5-25 words typically)

REQUIRED OUTPUT FORMAT:
You must respond in JSON format only:
{{
  "messages": [
    "first message text",
    "second message text if needed"
  ],
  "goal_advancement": "rapport_building/information_gathering/logistics_nudge/date_proposal/clarification/acknowledgement",
  "emotional_tone": "warm/friendly/curious/playful/neutral/enthusiastic"
}}

Examples:
{{
  "messages": ["That's so cool!", "How long have you been doing that?"],
  "goal_advancement": "information_gathering", 
  "emotional_tone": "curious"
}}

{{
  "messages": ["Coffee sounds perfect", "I know this amazing place downtown"],
  "goal_advancement": "logistics_nudge",
  "emotional_tone": "enthusiastic" 
}}"""
        
        return prompt
    
    def _format_memory_synopsis(self, synopsis: Dict[str, Any]) -> str:
        """Format memory synopsis for prompt"""
        if not synopsis:
            return "No information yet"
            
        sections = []
        
        # Interests
        interests = synopsis.get("fact_categories", {}).get("interests", [])
        if interests:
            interests_text = ", ".join([f["value"] for f in interests[:5]])
            sections.append(f"Interests: {interests_text}")
        
        # Personal info
        personal = synopsis.get("fact_categories", {}).get("personal_info", [])
        if personal:
            for fact in personal[:3]:
                sections.append(f"{fact['key']}: {fact['value']}")
        
        # Boundaries
        boundaries = synopsis.get("fact_categories", {}).get("boundaries", [])
        if boundaries:
            boundaries_text = ", ".join([f["value"] for f in boundaries])
            sections.append(f"Boundaries: {boundaries_text}")
        
        # Personality
        traits = synopsis.get("personality_traits", [])
        if traits:
            sections.append(f"Personality: {', '.join(traits)}")
        
        # Unresolved topics
        unresolved = synopsis.get("unresolved_topics", [])
        if unresolved:
            questions = [t["question"] for t in unresolved[:2]]
            sections.append(f"Recent questions: {'; '.join(questions)}")
        
        return "\n".join(sections) if sections else "Limited information available"
    
    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """Format constraints for prompt"""
        parts = []
        
        if constraints.get("max_length"):
            parts.append(f"Keep reply under {constraints['max_length']} words")
            
        if constraints.get("tone_adjustment"):
            parts.append(f"Tone should be {constraints['tone_adjustment']}")
            
        if constraints.get("content_restrictions"):
            for restriction in constraints["content_restrictions"]:
                parts.append(f"Important: {restriction}")
        
        return "\n".join(parts) if parts else "No specific constraints"
    
    def _format_emoji_usage(self, emoji_freq: Dict[str, float]) -> str:
        """Format emoji usage description"""
        if not emoji_freq:
            return "minimal emojis"
            
        total_freq = sum(emoji_freq.values())
        if total_freq > 0.3:
            return f"frequent emojis, especially {', '.join(list(emoji_freq.keys())[:3])}"
        elif total_freq > 0.1:
            return f"occasional emojis like {', '.join(list(emoji_freq.keys())[:2])}"
        else:
            return "sparse emoji use"
    
    def _get_stage_goal(self, stage: ProgressionStage) -> str:
        """Get conversation goal based on progression stage"""
        goals = {
            ProgressionStage.DISCOVERY: "Learn about their interests and build initial connection",
            ProgressionStage.RAPPORT: "Deepen the connection by finding common ground and showing genuine interest",
            ProgressionStage.LOGISTICS_CANDIDATE: "Subtly explore the possibility of meeting in person",
            ProgressionStage.PROPOSAL: "Suggest a specific activity and time to meet",
            ProgressionStage.NEGOTIATION: "Work together to find a mutually agreeable plan",
            ProgressionStage.CONFIRMATION: "Confirm the details and express excitement",
            ProgressionStage.POST_CONFIRMATION: "Maintain connection without changing plans"
        }
        
        return goals.get(stage, "Maintain friendly conversation")
    
    async def _call_llm_for_reply(self, prompt: str) -> str:
        """Call LLM to generate reply"""
        if settings.llm_provider == "openai":
            return await self._call_openai_for_reply(prompt)
        elif settings.llm_provider == "anthropic":
            return await self._call_anthropic_for_reply(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
    
    async def _call_openai_for_reply(self, prompt: str) -> str:
        """Call OpenAI for reply generation"""
        response = await self.httpx_client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.llm_model_name,
                "messages": [
                    {"role": "system", "content": "You are an expert at crafting natural, engaging WhatsApp messages that build connection while respecting boundaries."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result["choices"][0]["message"]["content"]
    
    async def _call_anthropic_for_reply(self, prompt: str) -> str:
        """Call Anthropic for reply generation"""
        response = await self.httpx_client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key.get_secret_value(),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": settings.llm_model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500,
                "system": "You are an expert at crafting natural, engaging WhatsApp messages that build connection while respecting boundaries."
            }
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result["content"][0]["text"]
    
    def _parse_llm_response(self, response: str) -> Tuple[str, Dict[str, Any]]:
        """Parse LLM response to extract reply and metadata"""
        try:
            data = json.loads(response)
            messages = data.get("messages", [])
            goal_advancement = data.get("goal_advancement")
            emotional_tone = data.get("emotional_tone")

            reply_text = "\n".join(messages) if messages else response.strip()
            meta_tags = {
                "goal_advancement": goal_advancement,
                "emotional_tone": emotional_tone
            }

            return reply_text, meta_tags
        except json.JSONDecodeError:
            # Fallback to old parsing if JSON is not found
            lines = response.strip().split('\n')
            
            reply_text = ""
            meta_tags = {}
            
            # Look for meta tags
            for line in lines:
                if line.startswith("Target goal advancement:"):
                    meta_tags["goal_advancement"] = line.split(":", 1)[1].strip()
                elif line.startswith("Emotional tone:"):
                    meta_tags["emotional_tone"] = line.split(":", 1)[1].strip()
                elif line.startswith("Reply:"):
                    # Everything after this is the reply
                    idx = lines.index(line)
                    reply_text = '\n'.join(lines[idx+1:]).strip()
                    break
                elif not line.startswith(("Target", "Emotional")) and line.strip():
                    # If no explicit "Reply:" marker, treat as reply text
                    reply_text += line + "\n"
            
            reply_text = reply_text.strip()
            
            # If still no reply text, use the whole response
            if not reply_text:
                reply_text = response.strip()
            
            return reply_text, meta_tags
    
    async def _post_process_reply(
        self,
        reply_text: str,
        contact: Contact,
        constraints: Dict[str, Any]
    ) -> str:
        """Post-process the generated reply"""
        # Enforce max length
        max_length = constraints.get("max_length", 150)
        words = reply_text.split()
        if len(words) > max_length:
            reply_text = ' '.join(words[:max_length]) + "..."
        
        # Add variety check
        recent_replies = await self.db_manager.get_recent_outbound_messages(
            contact_id=contact.id,
            limit=5
        )
        
        # Simple similarity check
        for recent in recent_replies:
            if recent.text_content and self._is_too_similar(reply_text, recent.text_content):
                # Add variation
                reply_text = self._add_variation(reply_text)
                break
        
        # Add hedging if needed
        if contact.progression_stage in [ProgressionStage.LOGISTICS_CANDIDATE, ProgressionStage.PROPOSAL]:
            reply_text = self._add_hedging(reply_text)
        
        # Ensure no hard commitments
        reply_text = self._soften_commitments(reply_text)
        
        return reply_text
    
    def _is_too_similar(self, text1: str, text2: str) -> bool:
        """Check if two texts are too similar"""
        # Simple check - in production, use better similarity metrics
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
            
        overlap = len(words1.intersection(words2))
        similarity = overlap / max(len(words1), len(words2))
        
        return similarity > 0.7
    
    def _add_variation(self, text: str) -> str:
        """Add variation to text"""
        variations = [
            ("Hey", "Hi"),
            ("How about", "What about"),
            ("Maybe we could", "Perhaps we could"),
            ("sounds good", "sounds great"),
            ("I'd love to", "I'd be happy to")
        ]
        
        for old, new in variations:
            if old.lower() in text.lower():
                text = text.replace(old, new)
                break
                
        return text
    
    def _add_hedging(self, text: str) -> str:
        """Add hedging language"""
        hedges = ["maybe", "perhaps", "if you'd like", "if you're interested"]
        
        # Check if already has hedging
        text_lower = text.lower()
        if any(hedge in text_lower for hedge in hedges):
            return text
        
        # Add hedge at beginning sometimes
        if random.random() < 0.3:
            text = f"Maybe {text[0].lower()}{text[1:]}"
        
        return text
    
    def _soften_commitments(self, text: str) -> str:
        """Soften any hard commitments"""
        replacements = [
            (r"I'll be there", "I should be able to make it"),
            (r"I'll definitely", "I'll try to"),
            (r"I promise", "I'll do my best to"),
            (r"for sure", "most likely"),
            (r"definitely", "probably")
        ]
        
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
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
        async with self.db_manager.async_session() as session:
            reply = OutboundReply(
                message_id=message_id,
                contact_id=contact_id,
                user_id=user_id,
                generated_text=reply_text,
                full_prompt_context_json=prompt_context,
                llm_meta_tags_json=meta_tags,
                status="pending"  # Will be updated when sent
            )
            
            session.add(reply)
            await session.commit()
    
    def _redact_prompt_context(self, prompt: str) -> Dict[str, Any]:
        """Redact sensitive information from prompt before storing"""
        # Store a summary instead of full prompt
        return {
            "prompt_length": len(prompt),
            "timestamp": datetime.utcnow().isoformat(),
            "llm_provider": settings.llm_provider,
            "model": settings.llm_model_name
        } 