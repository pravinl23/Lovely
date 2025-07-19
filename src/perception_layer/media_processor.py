"""
Media processing for audio transcription and image captioning
"""
import io
import base64
from typing import Optional, Dict, Any
import httpx
from PIL import Image
import numpy as np

from config.settings import settings
from src.utils.logging import get_logger
from src.api_control_plane.whatsapp_client import WhatsAppClient

logger = get_logger(__name__)


class MediaProcessor:
    """Handles media processing for WhatsApp messages"""
    
    def __init__(self):
        self.whatsapp_client = WhatsAppClient()
        self.httpx_client = httpx.AsyncClient(timeout=60.0)
        
    async def __aenter__(self):
        await self.whatsapp_client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.whatsapp_client.__aexit__(exc_type, exc_val, exc_tb)
        await self.httpx_client.aclose()
    
    async def process_media(
        self, 
        media_id: str, 
        media_type: str,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process media based on type"""
        result = {
            "media_id": media_id,
            "media_type": media_type,
            "processed": False,
            "extracted_text": None,
            "error": None
        }
        
        try:
            # Download media from WhatsApp
            media_content = await self.whatsapp_client.download_media(media_id)
            
            if media_type == "audio" and settings.enable_audio_transcription:
                result["extracted_text"] = await self.transcribe_audio(
                    media_content, 
                    mime_type
                )
                result["processed"] = True
                
            elif media_type == "image" and settings.enable_image_captioning:
                result["extracted_text"] = await self.caption_image(
                    media_content
                )
                result["processed"] = True
                
            elif media_type == "video":
                # For videos, we might extract first frame and caption it
                # For now, just note it's a video
                result["extracted_text"] = "[Video message]"
                result["processed"] = True
                
            else:
                result["extracted_text"] = f"[{media_type} message]"
                
        except Exception as e:
            logger.error(f"Error processing media: {str(e)}", extra={
                "media_id": media_id,
                "media_type": media_type
            }, exc_info=True)
            result["error"] = str(e)
            
        return result
    
    async def transcribe_audio(
        self, 
        audio_content: bytes, 
        mime_type: Optional[str] = None
    ) -> str:
        """Transcribe audio using OpenAI Whisper API"""
        try:
            if settings.llm_provider != "openai" or not settings.openai_api_key:
                return "[Audio message - transcription not available]"
                
            # Prepare audio file
            file_extension = self._get_audio_extension(mime_type)
            files = {
                "file": (f"audio.{file_extension}", audio_content, mime_type or "audio/mpeg")
            }
            
            # Call OpenAI Whisper API
            response = await self.httpx_client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}"
                },
                files=files,
                data={
                    "model": "whisper-1",
                    "response_format": "text"
                }
            )
            
            response.raise_for_status()
            transcription = response.text.strip()
            
            logger.info("Audio transcribed successfully", extra={
                "transcription_length": len(transcription)
            })
            
            return transcription or "[Audio message - no speech detected]"
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}", exc_info=True)
            return "[Audio message - transcription failed]"
    
    async def caption_image(self, image_content: bytes) -> str:
        """Generate image caption using vision model"""
        try:
            if settings.llm_provider == "openai" and settings.openai_api_key:
                return await self._caption_with_openai(image_content)
            elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
                return await self._caption_with_anthropic(image_content)
            else:
                return "[Image message - captioning not available]"
                
        except Exception as e:
            logger.error(f"Image captioning failed: {str(e)}", exc_info=True)
            return "[Image message - captioning failed]"
    
    async def _caption_with_openai(self, image_content: bytes) -> str:
        """Use OpenAI Vision API for image captioning"""
        # Convert image to base64
        base64_image = base64.b64encode(image_content).decode('utf-8')
        
        response = await self.httpx_client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image in one or two sentences, focusing on the main subject and any important details."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150
            }
        )
        
        response.raise_for_status()
        result = response.json()
        
        caption = result["choices"][0]["message"]["content"].strip()
        logger.info("Image captioned successfully", extra={
            "caption_length": len(caption)
        })
        
        return f"[Image: {caption}]"
    
    async def _caption_with_anthropic(self, image_content: bytes) -> str:
        """Use Anthropic Claude Vision for image captioning"""
        # Convert image to base64
        base64_image = base64.b64encode(image_content).decode('utf-8')
        
        response = await self.httpx_client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key.get_secret_value(),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-3-sonnet-20240229",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image in one or two sentences, focusing on the main subject and any important details."
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150
            }
        )
        
        response.raise_for_status()
        result = response.json()
        
        caption = result["content"][0]["text"].strip()
        logger.info("Image captioned successfully", extra={
            "caption_length": len(caption)
        })
        
        return f"[Image: {caption}]"
    
    def _get_audio_extension(self, mime_type: Optional[str]) -> str:
        """Get file extension from MIME type"""
        mime_to_extension = {
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg",
            "audio/wav": "wav",
            "audio/webm": "webm",
            "audio/aac": "aac",
            "audio/mp4": "m4a"
        }
        
        if mime_type and mime_type in mime_to_extension:
            return mime_to_extension[mime_type]
        
        # Default to mp3
        return "mp3" 