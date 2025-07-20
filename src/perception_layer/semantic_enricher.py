"""
Semantic enrichment for extracting intents, entities, sentiment, etc.
"""
import json
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime
import re

from config.settings import settings
from src.utils.logging import get_logger
from src.perception_layer.models import (
    MessageAnnotations, Intent, Sentiment, Entity, TemporalMention
)

logger = get_logger(__name__)


class SemanticEnricher:
    """Extracts semantic information from messages using LLM"""
    
    def __init__(self):
        self.httpx_client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.httpx_client.aclose()
    
    async def enrich_message(self, message_text: str) -> MessageAnnotations:
        """Extract semantic annotations from message text"""
        if not message_text or not message_text.strip():
            return MessageAnnotations()
            
        try:
            # Use LLM to extract annotations
            extraction_result = await self._extract_with_llm(message_text)
            
            # Parse the result into our annotation structure
            annotations = self._parse_extraction_result(extraction_result)
            
            logger.info("Message enriched successfully", extra={
                "intents_count": len(annotations.intents),
                "entities_count": len(annotations.entities),
                "sentiment": annotations.sentiment.value if annotations.sentiment else None
            })
            
            return annotations
            
        except Exception as e:
            logger.error(f"Semantic enrichment failed: {str(e)}", exc_info=True)
            return MessageAnnotations()
    
    async def _extract_with_llm(self, message_text: str) -> Dict[str, Any]:
        """Use LLM to extract semantic information"""
        prompt = f"""You are an intelligent assistant analyzing a WhatsApp message. Extract the following from the message:

1. **Intent:** What is the primary purpose of this message? Choose from: 'banter', 'logistics', 'scheduling', 'question', 'sharing_info', 'boundary', 'refusal', 'enthusiasm', 'acknowledgement', 'greeting', 'farewell'. You can list multiple if applicable.

2. **Entities:** Identify any mentions of:
   - person (names or references to people)
   - location (places, venues, addresses)
   - date (specific dates or day references)
   - time (specific times or time ranges)
   - food (dishes, restaurants, cuisine types)
   - hobby (activities, interests, sports)
   - job_title (professions, work roles)
   - event (concerts, meetings, parties, etc.)
   - object (physical items mentioned)
   List them as key-value pairs.

3. **Temporal Mentions:** Extract and normalize any explicit or implicit date/time references. Provide:
   - original_text: the exact phrase from the message
   - normalized_value: ISO 8601 format if possible (use current date as reference: {datetime.now().isoformat()})
   - relative_reference: clear phrase like "tomorrow", "next Friday", etc.

4. **Sentiment/Affect:** Describe the overall emotional tone. Choose from: 'positive', 'neutral', 'negative', 'excited', 'annoyed', 'curious', 'warm'.

5. **Key Phrases/Topics:** Identify 1-3 most important phrases or topics discussed.

6. **Questions Asked:** List any explicit questions posed in the message.

Message: "{message_text}"

Provide the output in JSON format with keys: intents, entities, temporal_mentions, sentiment, key_phrases, questions."""

        return await self._call_openai(prompt)
    
    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API for extraction"""
        response = await self.httpx_client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a precise information extraction assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
        )
        
        response.raise_for_status()
        result = response.json()
        
        try:
            return json.loads(result["choices"][0]["message"]["content"])
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return {}

    
    def _parse_extraction_result(self, result: Dict[str, Any]) -> MessageAnnotations:
        """Parse LLM extraction result into MessageAnnotations"""
        annotations = MessageAnnotations()
        
        # Parse intents
        for intent_str in result.get("intents", []):
            try:
                intent = Intent(intent_str.lower())
                annotations.intents.append(intent)
            except ValueError:
                logger.warning(f"Unknown intent: {intent_str}")
        
        # Parse entities
        entities_data = result.get("entities", {})
        if isinstance(entities_data, dict):
            for entity_type, values in entities_data.items():
                if isinstance(values, list):
                    for value in values:
                        annotations.entities.append(
                            Entity(type=entity_type, value=value)
                        )
                else:
                    annotations.entities.append(
                        Entity(type=entity_type, value=str(values))
                    )
        
        # Parse temporal mentions
        for tm_data in result.get("temporal_mentions", []):
            if isinstance(tm_data, dict):
                annotations.temporal_mentions.append(
                    TemporalMention(
                        original_text=tm_data.get("original_text", ""),
                        normalized_value=tm_data.get("normalized_value"),
                        relative_reference=tm_data.get("relative_reference")
                    )
                )
        
        # Parse sentiment
        sentiment_str = result.get("sentiment")
        if sentiment_str:
            try:
                annotations.sentiment = Sentiment(sentiment_str.lower())
            except ValueError:
                logger.warning(f"Unknown sentiment: {sentiment_str}")
        
        # Parse key phrases
        annotations.key_phrases = result.get("key_phrases", [])
        
        # Parse questions
        annotations.questions = result.get("questions", [])
        
        return annotations
    
    async def batch_enrich(
        self, 
        messages: List[str]
    ) -> List[MessageAnnotations]:
        """Enrich multiple messages in batch"""
        # For now, process sequentially
        # Could be optimized with concurrent processing
        results = []
        
        for message in messages:
            annotations = await self.enrich_message(message)
            results.append(annotations)
            
        return results 