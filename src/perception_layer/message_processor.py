"""
Message processor that orchestrates perception layer components
"""
from datetime import datetime
from typing import Dict, Any, Optional

from src.perception_layer.models import Message, MediaType
from src.perception_layer.media_processor import MediaProcessor
from src.perception_layer.semantic_enricher import SemanticEnricher
from src.core.message_queue import QueueMessage
from src.persistence_layer.db_manager import DatabaseManager
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)


class MessageProcessor:
    """Processes incoming WhatsApp messages through the perception pipeline"""
    
    def __init__(self):
        self.media_processor = MediaProcessor()
        self.semantic_enricher = SemanticEnricher()
        self.db_manager = DatabaseManager()
        
    async def __aenter__(self):
        await self.media_processor.__aenter__()
        await self.semantic_enricher.__aenter__()
        await self.db_manager.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.media_processor.__aexit__(exc_type, exc_val, exc_tb)
        await self.semantic_enricher.__aexit__(exc_type, exc_val, exc_tb)
        await self.db_manager.__aexit__(exc_type, exc_val, exc_tb)
    
    async def process_incoming_message(self, queue_message: QueueMessage):
        """Main entry point for processing incoming messages"""
        try:
            data = queue_message.data
            
            # Create canonical message
            message = await self._create_canonical_message(data)
            
            # Process media if applicable
            if message.media_type != "text" and message.media_id:
                await self._process_media_content(message, data)
            
            # Perform semantic enrichment
            if message.text_content:
                message.annotations = await self.semantic_enricher.enrich_message(
                    message.text_content
                )
            
            # Store message in database
            await self.db_manager.store_message(message)
            
            # Generate embeddings for vector storage
            if message.text_content:
                await self.db_manager.store_message_embedding(
                    message_id=message.message_id,
                    text=message.text_content
                )
            
            # Trigger cognition layer processing
            await self._trigger_cognition_processing(message)
            
            logger.info("Message processed successfully", extra={
                "message_id": message.message_id,
                "conversation_id": message.conversation_id,
                "media_type": message.media_type
            })
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", extra={
                "queue_message_id": queue_message.id
            }, exc_info=True)
            raise
    
    async def _create_canonical_message(
        self, 
        webhook_data: Dict[str, Any]
    ) -> Message:
        """Create a canonical message from webhook data"""
        # Extract base fields
        message_id = webhook_data["message_id"]
        sender_id = webhook_data["from"]
        timestamp = datetime.fromtimestamp(int(webhook_data["timestamp"]))
        message_type = webhook_data["type"]
        
        # Determine conversation ID (contact ID)
        conversation_id = sender_id
        
        # Get our bot's ID (receiver)
        phone_number_id = webhook_data.get("phone_number_id", "")
        receiver_id = phone_number_id  # Simplified for now
        
        # Extract text content based on message type
        text_content = ""
        media_type = self._map_message_type(message_type)
        
        if message_type == "text":
            text_content = webhook_data.get("text", "")
            
        elif message_type == "interactive":
            # Extract text from interactive messages
            if webhook_data.get("interactive_type") == "button_reply":
                text_content = webhook_data.get("button_text", "")
            elif webhook_data.get("interactive_type") == "list_reply":
                text_content = webhook_data.get("list_item_title", "")
                
        elif message_type == "location":
            # Format location as text
            lat = webhook_data.get("latitude")
            lon = webhook_data.get("longitude")
            name = webhook_data.get("location_name", "")
            address = webhook_data.get("location_address", "")
            
            text_content = f"[Location"
            if name:
                text_content += f": {name}"
            if address:
                text_content += f" at {address}"
            text_content += f" ({lat}, {lon})]"
        
        # Create message object
        message = Message(
            message_id=message_id,
            conversation_id=conversation_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            timestamp=timestamp,
            text_content=text_content,
            media_type=media_type,
            media_id=webhook_data.get("media_id"),
            is_inbound=True,
            raw_webhook_payload=webhook_data.get("raw_message")
        )
        
        # Add additional metadata
        if message_type in ["image", "video", "document"]:
            message.caption = webhook_data.get("caption", "")
            
        if message_type == "document":
            message.filename = webhook_data.get("filename", "")
            
        if message_type == "location":
            message.location_data = {
                "latitude": webhook_data.get("latitude"),
                "longitude": webhook_data.get("longitude"),
                "name": webhook_data.get("location_name"),
                "address": webhook_data.get("location_address")
            }
            
        if message_type == "reaction":
            message.reaction_data = {
                "emoji": webhook_data.get("reaction_emoji"),
                "message_id": webhook_data.get("reaction_message_id")
            }
            
        if message_type == "interactive":
            message.interactive_data = {
                "type": webhook_data.get("interactive_type"),
                "payload": webhook_data.get("button_payload") or webhook_data.get("list_item_id"),
                "title": webhook_data.get("button_text") or webhook_data.get("list_item_title")
            }
        
        return message
    
    async def _process_media_content(
        self, 
        message: Message, 
        webhook_data: Dict[str, Any]
    ):
        """Process media content and update message"""
        result = await self.media_processor.process_media(
            media_id=message.media_id,
            media_type=message.media_type,
            mime_type=webhook_data.get("media_mime_type")
        )
        
        if result["processed"] and result["extracted_text"]:
            # Update message text content with extracted text
            if message.caption:
                message.text_content = f"{result['extracted_text']} Caption: {message.caption}"
            else:
                message.text_content = result["extracted_text"]
                
        # Store media URL if available
        # Note: In production, you'd store the media in object storage
        # and update message.media_url with the permanent URL
    
    async def _trigger_cognition_processing(self, message: Message):
        """Trigger cognition layer to process the message"""
        from src.core.message_queue import MessageQueue
        
        # Create a queue message for cognition layer
        cognition_data = {
            "message_id": message.message_id,
            "conversation_id": message.conversation_id,
            "timestamp": message.timestamp.isoformat(),
            "trigger": "new_message"
        }
        
        queue = MessageQueue()
        await queue.enqueue(
            queue_name="cognition_tasks",
            data=cognition_data,
            priority=1  # High priority for new messages
        )
    
    def _map_message_type(self, webhook_type: str) -> MediaType:
        """Map WhatsApp message type to our MediaType"""
        type_mapping = {
            "text": "text",
            "image": "image",
            "audio": "audio",
            "video": "video",
            "document": "document",
            "sticker": "sticker",
            "location": "location",
            "interactive": "text",  # Interactive messages are treated as text
            "reaction": "text",  # Reactions are treated as text
        }
        
        return type_mapping.get(webhook_type, "unknown") 