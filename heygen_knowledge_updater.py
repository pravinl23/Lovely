#!/usr/bin/env python3
"""
HeyGen Knowledge Base Updater
Updates HeyGen knowledge base with conversation context from Supabase
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HeyGenKnowledgeUpdater:
    """Updates HeyGen knowledge base with conversation context"""
    
    def __init__(self, 
                 heygen_api_key: str,
                 supabase_url: str, 
                 supabase_service_key: str,
                 knowledge_base_id: str = "bfa1e9e954c44662836e4b98dab05766"):
        self.heygen_api_key = heygen_api_key
        self.supabase_url = supabase_url
        self.supabase_service_key = supabase_service_key
        self.knowledge_base_id = knowledge_base_id
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def get_all_messages_from_supabase(self) -> List[Dict[str, Any]]:
        """Fetch all messages from Supabase using REST API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.supabase_service_key}",
                "Content-Type": "application/json",
                "apikey": self.supabase_service_key
            }
            
            # Get messages with contact information for context
            url = f"{self.supabase_url}/rest/v1/messages"
            params = {
                "select": "*, contacts(name, whatsapp_id)",
                "order": "timestamp.asc",
                "limit": 1000  # Adjust based on your needs
            }
            
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            messages = response.json()
            logger.info(f"Retrieved {len(messages)} messages from Supabase")
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching messages from Supabase: {str(e)}")
            return []
    
    def format_conversation_context(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a readable conversation context"""
        if not messages:
            return "No previous conversation history available."
        
        context_lines = []
        context_lines.append("=== PREVIOUS CONVERSATION HISTORY ===")
        context_lines.append("This is context from previous conversations. Reference this information to maintain consistency and build on past interactions.\n")
        
        # Group messages by contact for better organization
        contacts_messages = {}
        for msg in messages:
            contact_name = "Unknown"
            contact_id = msg.get('contact_id', 'unknown')
            
            if msg.get('contacts'):
                contact_name = msg['contacts'].get('name') or msg['contacts'].get('whatsapp_id', 'Unknown')
            
            if contact_id not in contacts_messages:
                contacts_messages[contact_id] = {
                    'name': contact_name,
                    'messages': []
                }
            
            contacts_messages[contact_id]['messages'].append(msg)
        
        # Format conversations
        for contact_id, contact_data in contacts_messages.items():
            contact_name = contact_data['name']
            messages_list = contact_data['messages']
            
            context_lines.append(f"\n--- Conversation with {contact_name} ---")
            
            for msg in messages_list[-20:]:  # Last 20 messages per contact
                timestamp = msg.get('timestamp', '')[:19]  # Remove timezone info for readability
                direction = "THEM" if msg.get('is_inbound') else "YOU"
                content = msg.get('text_content', '').strip()
                
                if content:  # Only include messages with text content
                    context_lines.append(f"[{timestamp}] {direction}: {content}")
        
        context_lines.append("\n=== END CONVERSATION HISTORY ===\n")
        return "\n".join(context_lines)
    
    async def update_heygen_knowledge_base(self, conversation_context: str) -> bool:
        """Update HeyGen knowledge base with new context"""
        try:
            # Base personality prompt as specified
            base_prompt = """You are a flirtatious young thug. Just be very nonchalant. Act disinterested but super flirtatious to almost the point of being pushy. You wanna get in the user's pants. Talk in strong slang and don't be too professional. Talk like the link shows. Speak in AAVE. Don't show too much emotion. You're talking to a woman. Be open to booking dates. Don't be corny at all. If you think you're being corny, just give a short black response instead. Act like a dick. A super arrogant guy."""
            
            # Combine with conversation context
            full_knowledge = f"{base_prompt}\n\n{conversation_context}"
            
            # HeyGen API endpoint for updating knowledge base
            url = f"https://api.heygen.com/v1/knowledge_base/{self.knowledge_base_id}"
            
            headers = {
                "X-Api-Key": self.heygen_api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "content": full_knowledge
            }
            
            response = await self.client.put(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info("Successfully updated HeyGen knowledge base")
                return True
            else:
                logger.error(f"HeyGen API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating HeyGen knowledge base: {str(e)}")
            return False
    
    async def update_knowledge_with_conversation_history(self) -> bool:
        """Main method to update knowledge base with full conversation context"""
        try:
            logger.info("Fetching conversation history from Supabase...")
            messages = await self.get_all_messages_from_supabase()
            
            logger.info("Formatting conversation context...")
            conversation_context = self.format_conversation_context(messages)
            
            logger.info("Updating HeyGen knowledge base...")
            success = await self.update_heygen_knowledge_base(conversation_context)
            
            if success:
                logger.info("✅ Knowledge base updated successfully with conversation history")
            else:
                logger.error("❌ Failed to update knowledge base")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in knowledge update process: {str(e)}")
            return False

# Configuration - Update these with your actual values
HEYGEN_API_KEY = "YOUR_HEYGEN_API_KEY"  # Replace with actual key
SUPABASE_URL = "YOUR_SUPABASE_URL"      # Replace with actual URL  
SUPABASE_SERVICE_KEY = "YOUR_SUPABASE_SERVICE_KEY"  # Replace with actual key

async def main():
    """Test the knowledge updater"""
    async with HeyGenKnowledgeUpdater(
        heygen_api_key=HEYGEN_API_KEY,
        supabase_url=SUPABASE_URL,
        supabase_service_key=SUPABASE_SERVICE_KEY
    ) as updater:
        success = await updater.update_knowledge_with_conversation_history()
        return success

if __name__ == "__main__":
    asyncio.run(main()) 