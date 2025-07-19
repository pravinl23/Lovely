"""
WhatsApp Webhook Handler
Handles incoming webhooks from WhatsApp Cloud API
"""
from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse
import json
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from config.settings import settings
from src.api_control_plane.whatsapp_client import WhatsAppClient
from src.core.message_queue import MessageQueue
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])

# Initialize message queue
message_queue = MessageQueue()


@router.get("")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
) -> PlainTextResponse:
    """
    Verify webhook endpoint for WhatsApp
    This is called by Meta when setting up the webhook
    """
    logger.info("Webhook verification request received", extra={
        "hub_mode": hub_mode,
        "has_token": bool(hub_verify_token),
        "has_challenge": bool(hub_challenge)
    })
    
    if hub_mode == "subscribe":
        # Verify the token matches our configured token
        if hub_verify_token == settings.whatsapp_webhook_verify_token.get_secret_value():
            logger.info("Webhook verification successful")
            return PlainTextResponse(content=hub_challenge)
        else:
            logger.warning("Webhook verification failed - token mismatch")
            raise HTTPException(status_code=403, detail="Verification token mismatch")
    
    logger.warning("Invalid webhook verification request")
    raise HTTPException(status_code=400, detail="Invalid request")


@router.post("")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> Response:
    """
    Receive webhook events from WhatsApp
    Process them asynchronously to avoid timeouts
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not WhatsAppClient.verify_webhook_signature(
        body, 
        signature, 
        settings.whatsapp_webhook_secret.get_secret_value()
    ):
        logger.warning("Invalid webhook signature", extra={
            "signature": signature[:20] + "..."  # Log partial signature for debugging
        })
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse the webhook payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Failed to parse webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Extract webhook ID for deduplication
    webhook_id = payload.get("entry", [{}])[0].get("id", "")
    
    logger.info("Webhook received", extra={
        "webhook_id": webhook_id,
        "object_type": payload.get("object"),
        "entry_count": len(payload.get("entry", []))
    })
    
    # Process webhook asynchronously
    background_tasks.add_task(process_webhook_async, payload)
    
    # Immediately return 200 OK to acknowledge receipt
    return Response(status_code=200)


async def process_webhook_async(payload: Dict[str, Any]) -> None:
    """
    Process webhook payload asynchronously
    This runs in the background after acknowledging the webhook
    """
    try:
        # WhatsApp sends webhooks with this structure
        if payload.get("object") != "whatsapp_business_account":
            logger.warning("Received non-WhatsApp webhook", extra={
                "object_type": payload.get("object")
            })
            return
        
        # Process each entry
        for entry in payload.get("entry", []):
            entry_id = entry.get("id")
            
            # Process each change in the entry
            for change in entry.get("changes", []):
                field = change.get("field")
                value = change.get("value", {})
                
                if field == "messages":
                    # Process incoming messages
                    await process_messages(value)
                    
                elif field == "statuses":
                    # Process message status updates
                    await process_status_updates(value)
                    
                else:
                    logger.debug(f"Ignoring webhook field: {field}")
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)


async def process_messages(value: Dict[str, Any]) -> None:
    """Process incoming messages from webhook"""
    metadata = value.get("metadata", {})
    phone_number_id = metadata.get("phone_number_id")
    
    # Process each message
    for message in value.get("messages", []):
        try:
            # Extract message details
            message_data = {
                "message_id": message.get("id"),
                "from": message.get("from"),  # Sender's WhatsApp ID
                "timestamp": message.get("timestamp"),
                "type": message.get("type"),
                "raw_message": message,
                "phone_number_id": phone_number_id,
                "received_at": datetime.utcnow().isoformat()
            }
            
            # Extract message content based on type
            message_type = message.get("type")
            
            if message_type == "text":
                message_data["text"] = message.get("text", {}).get("body", "")
                
            elif message_type in ["image", "audio", "video", "document", "sticker"]:
                media_data = message.get(message_type, {})
                message_data["media_id"] = media_data.get("id")
                message_data["media_mime_type"] = media_data.get("mime_type")
                message_data["media_sha256"] = media_data.get("sha256")
                
                # Some media types have captions
                if message_type in ["image", "video", "document"]:
                    message_data["caption"] = media_data.get("caption", "")
                    
                # Documents have filenames
                if message_type == "document":
                    message_data["filename"] = media_data.get("filename", "")
                    
            elif message_type == "location":
                location = message.get("location", {})
                message_data["latitude"] = location.get("latitude")
                message_data["longitude"] = location.get("longitude")
                message_data["location_name"] = location.get("name", "")
                message_data["location_address"] = location.get("address", "")
                
            elif message_type == "interactive":
                # Handle button replies and list replies
                interactive = message.get("interactive", {})
                message_data["interactive_type"] = interactive.get("type")
                
                if interactive.get("type") == "button_reply":
                    message_data["button_payload"] = interactive.get("button_reply", {}).get("id")
                    message_data["button_text"] = interactive.get("button_reply", {}).get("title")
                elif interactive.get("type") == "list_reply":
                    message_data["list_item_id"] = interactive.get("list_reply", {}).get("id")
                    message_data["list_item_title"] = interactive.get("list_reply", {}).get("title")
                    
            elif message_type == "reaction":
                reaction = message.get("reaction", {})
                message_data["reaction_emoji"] = reaction.get("emoji")
                message_data["reaction_message_id"] = reaction.get("message_id")
                
            else:
                logger.warning(f"Unknown message type: {message_type}")
            
            # Add to processing queue
            await message_queue.enqueue(
                queue_name="incoming_messages",
                data=message_data,
                priority=1  # All incoming messages have same priority
            )
            
            logger.info(f"Message queued for processing", extra={
                "message_id": message_data["message_id"],
                "message_type": message_type,
                "from": message_data["from"]
            })
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", extra={
                "message": message
            }, exc_info=True)


async def process_status_updates(value: Dict[str, Any]) -> None:
    """Process message status updates"""
    # Process each status update
    for status in value.get("statuses", []):
        try:
            status_data = {
                "message_id": status.get("id"),
                "recipient_id": status.get("recipient_id"),
                "status": status.get("status"),  # sent, delivered, read, failed
                "timestamp": status.get("timestamp"),
                "errors": status.get("errors", [])
            }
            
            # Log status updates
            logger.info(f"Message status update", extra={
                "message_id": status_data["message_id"],
                "status": status_data["status"],
                "recipient": status_data["recipient_id"]
            })
            
            # Queue status update for processing (lower priority)
            await message_queue.enqueue(
                queue_name="status_updates",
                data=status_data,
                priority=5
            )
            
            # Handle failed messages
            if status_data["status"] == "failed" and status_data["errors"]:
                logger.error(f"Message delivery failed", extra={
                    "message_id": status_data["message_id"],
                    "errors": status_data["errors"]
                })
                
        except Exception as e:
            logger.error(f"Error processing status update: {str(e)}", extra={
                "status": status
            }, exc_info=True)


# Helper function to extract contact info from messages
def extract_contact_info(message: Dict[str, Any]) -> Dict[str, Any]:
    """Extract contact information from a message"""
    profile = message.get("profile", {})
    return {
        "whatsapp_id": message.get("from"),
        "name": profile.get("name", ""),
        "profile_picture": profile.get("profile_picture", "")
    } 