"""
WhatsApp Cloud API Client
Handles all interactions with the WhatsApp Business API
"""
import httpx
import json
import hmac
import hashlib
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, timedelta
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

MessageType = Literal["text", "image", "audio", "video", "document", "location", "sticker", "template"]


class WhatsAppAPIError(Exception):
    """Custom exception for WhatsApp API errors"""
    def __init__(self, message: str, error_code: Optional[str] = None, status_code: Optional[int] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class TokenExpiredError(WhatsAppAPIError):
    """Raised when the WhatsApp access token has expired"""
    def __init__(self, message: str):
        super().__init__(message, error_code="190", status_code=401)


class WhatsAppClient:
    """Client for interacting with WhatsApp Cloud API"""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self):
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.access_token = settings.whatsapp_access_token.get_secret_value()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
        )
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError)
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to WhatsApp API with retry logic"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_data = e.response.json() if e.response.content else {}
            error_message = error_data.get("error", {}).get("message", str(e))
            error_code = error_data.get("error", {}).get("code")
            
            # Check for token expiration specifically
            if e.response.status_code == 401 and "access token" in error_message.lower():
                logger.error(f"WhatsApp access token has expired: {error_message}")
                logger.error(" FIX REQUIRED: Get a fresh access token from Meta for Developers")
                logger.error(" Go to: https://developers.facebook.com/apps/")
                logger.error(" Select your app > WhatsApp > API Setup")
                logger.error(" Generate a new temporary access token")
                logger.error(" Update WHATSAPP_ACCESS_TOKEN in your .env file")
                
                raise TokenExpiredError(
                    f"WhatsApp access token expired. Get a fresh token from Meta for Developers: {error_message}"
                )
            
            logger.error(f"WhatsApp API error: {error_message}", extra={
                "status_code": e.response.status_code,
                "error_code": error_code,
                "endpoint": endpoint
            })
            
            # Handle rate limiting specifically
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                raise
                
            raise WhatsAppAPIError(
                message=error_message,
                error_code=error_code,
                status_code=e.response.status_code
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in WhatsApp API request: {str(e)}")
            raise
    
    async def send_text_message(
        self, 
        to: str, 
        text: str,
        preview_url: bool = True
    ) -> Dict[str, Any]:
        """Send a text message to a WhatsApp number"""
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text
            }
        }
        
        response = await self._make_request(
            method="POST",
            endpoint=f"{self.phone_number_id}/messages",
            data=data
        )
        
        logger.info(f"Text message sent to {to}", extra={
            "message_id": response.get("messages", [{}])[0].get("id"),
            "contact_id": to
        })
        
        return response
    
    async def send_media_message(
        self,
        to: str,
        media_type: Literal["image", "audio", "video", "document"],
        media_url: Optional[str] = None,
        media_id: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a media message (image, audio, video, document)"""
        if not media_url and not media_id:
            raise ValueError("Either media_url or media_id must be provided")
            
        media_object = {}
        if media_id:
            media_object["id"] = media_id
        else:
            media_object["link"] = media_url
            
        if caption and media_type in ["image", "video", "document"]:
            media_object["caption"] = caption
            
        if filename and media_type == "document":
            media_object["filename"] = filename
            
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": media_type,
            media_type: media_object
        }
        
        response = await self._make_request(
            method="POST",
            endpoint=f"{self.phone_number_id}/messages",
            data=data
        )
        
        logger.info(f"Media message ({media_type}) sent to {to}", extra={
            "message_id": response.get("messages", [{}])[0].get("id"),
            "contact_id": to,
            "media_type": media_type
        })
        
        return response
    
    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send a pre-approved template message"""
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components:
            data["template"]["components"] = components
            
        response = await self._make_request(
            method="POST",
            endpoint=f"{self.phone_number_id}/messages",
            data=data
        )
        
        logger.info(f"Template message sent to {to}", extra={
            "message_id": response.get("messages", [{}])[0].get("id"),
            "contact_id": to,
            "template_name": template_name
        })
        
        return response
    
    async def download_media(self, media_id: str) -> bytes:
        """Download media content from WhatsApp"""
        # First, get the media URL
        media_info = await self._make_request(
            method="GET",
            endpoint=media_id
        )
        
        media_url = media_info.get("url")
        if not media_url:
            raise WhatsAppAPIError("No media URL found in response")
            
        # Download the actual media
        response = await self.client.get(
            media_url,
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        response.raise_for_status()
        
        logger.info(f"Media downloaded successfully", extra={
            "media_id": media_id,
            "content_length": len(response.content)
        })
        
        return response.content
    
    async def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark a message as read"""
        data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        response = await self._make_request(
            method="POST",
            endpoint=f"{self.phone_number_id}/messages",
            data=data
        )
        
        logger.debug(f"Message marked as read", extra={
            "message_id": message_id
        })
        
        return response
    
    async def get_phone_number_info(self) -> Dict[str, Any]:
        """Get information about the WhatsApp phone number"""
        response = await self._make_request(
            method="GET",
            endpoint=self.phone_number_id,
            params={"fields": "display_phone_number,verified_name,quality_rating"}
        )
        
        logger.info("Phone number info retrieved", extra={
            "phone_number": response.get("display_phone_number"),
            "quality_rating": response.get("quality_rating")
        })
        
        return response
    
    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature from WhatsApp"""
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected_signature}", signature)
    
    async def send_whatsapp_message(
        self,
        contact_id: str,
        message_type: MessageType,
        content: str,
        media_url: Optional[str] = None,
        media_id: Optional[str] = None,
        caption: Optional[str] = None,
        template_name: Optional[str] = None,
        template_params: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Unified method to send any type of WhatsApp message"""
        try:
            if message_type == "text":
                return await self.send_text_message(to=contact_id, text=content)
                
            elif message_type in ["image", "audio", "video", "document"]:
                return await self.send_media_message(
                    to=contact_id,
                    media_type=message_type,
                    media_url=media_url,
                    media_id=media_id,
                    caption=caption
                )
                
            elif message_type == "template":
                if not template_name:
                    raise ValueError("template_name is required for template messages")
                return await self.send_template_message(
                    to=contact_id,
                    template_name=template_name,
                    components=template_params
                )
                
            else:
                raise ValueError(f"Unsupported message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Failed to send message to {contact_id}: {str(e)}")
            raise 