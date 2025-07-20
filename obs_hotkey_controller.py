#!/usr/bin/env python3
"""
OBS Hotkey Controller with HeyGen Knowledge Base Integration
Requires: pip install obsws-python keyboard httpx
"""

import asyncio
import subprocess
import sys
from typing import Optional
import logging

try:
    import obsws_python as obs
    import keyboard
    import httpx
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Install with: pip install obsws-python keyboard httpx")
    sys.exit(1)

from heygen_knowledge_updater import HeyGenKnowledgeUpdater

# Configuration
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = "uBbyri7iLbK4RYke"  # Set if you have WebSocket password enabled

# Hotkey configuration
START_HOTKEY = "f9"  # Change to your preferred key
STOP_HOTKEY = "f10"  # Change to your preferred key

# Browser source name (change to match your OBS source name)
BROWSER_SOURCE_NAME = "Browser"

# Commands to run
START_COMMAND = ["echo", "Starting recording..."]  # Replace with your command
STOP_COMMAND = ["echo", "Recording stopped."]     # Replace with your command

# HeyGen and Supabase Configuration
HEYGEN_API_KEY = "YOUR_HEYGEN_API_KEY"  # Replace with your actual HeyGen API key
SUPABASE_URL = "YOUR_SUPABASE_URL"      # Replace with your Supabase URL
SUPABASE_SERVICE_KEY = "YOUR_SUPABASE_SERVICE_KEY"  # Replace with your Supabase service key
KNOWLEDGE_BASE_ID = "bfa1e9e954c44662836e4b98dab05766"  # Your HeyGen knowledge base ID

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OBSController:
    def __init__(self):
        self.client: Optional[obs.ReqClient] = None
        self.is_recording = False
        
    def connect(self):
        """Connect to OBS WebSocket"""
        try:
            self.client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
            logger.info("Connected to OBS WebSocket")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OBS: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from OBS"""
        if self.client:
            self.client.disconnect()
            logger.info("Disconnected from OBS")
    
    def start_recording_sequence(self):
        """Execute start recording sequence"""
        if self.is_recording:
            logger.warning("Already recording!")
            return
        
        try:
            # 1. Run start command
            logger.info("Running start command...")
            subprocess.run(START_COMMAND, check=True)
            
            # 2. Update HeyGen knowledge base with conversation history
            logger.info("Updating HeyGen knowledge base with conversation history...")
            asyncio.run(self._update_heygen_knowledge())
            
            # 3. Make browser source visible
            logger.info(f"Making '{BROWSER_SOURCE_NAME}' visible...")
            # Get current scene name
            current_scene = self.client.get_current_program_scene()
            scene_name = current_scene.current_program_scene_name
            
            self.client.set_scene_item_enabled(
                scene_name,
                self.get_source_id(BROWSER_SOURCE_NAME),
                True
            )
            
            # 4. Start recording
            logger.info("Starting OBS recording...")
            self.client.start_record()
            
            self.is_recording = True
            logger.info("✅ Recording sequence started!")
            
        except Exception as e:
            logger.error(f"Error in start sequence: {e}")
    
    def stop_recording_sequence(self):
        """Execute stop recording sequence"""
        if not self.is_recording:
            logger.warning("Not currently recording!")
            return
        
        try:
            # 1. Stop recording
            logger.info("Stopping OBS recording...")
            self.client.stop_record()
            
            # 2. Make browser source invisible
            logger.info(f"Making '{BROWSER_SOURCE_NAME}' invisible...")
            # Get current scene name
            current_scene = self.client.get_current_program_scene()
            scene_name = current_scene.current_program_scene_name
            
            self.client.set_scene_item_enabled(
                scene_name,
                self.get_source_id(BROWSER_SOURCE_NAME),
                False
            )
            
            # 3. Run stop command
            logger.info("Running stop command...")
            subprocess.run(STOP_COMMAND, check=True)
            
            self.is_recording = False
            logger.info("✅ Recording sequence stopped!")
            
        except Exception as e:
            logger.error(f"Error in stop sequence: {e}")
    
    async def _update_heygen_knowledge(self):
        """Update HeyGen knowledge base with conversation context"""
        try:
            # Check if credentials are configured
            if (HEYGEN_API_KEY == "YOUR_HEYGEN_API_KEY" or 
                SUPABASE_URL == "YOUR_SUPABASE_URL" or 
                SUPABASE_SERVICE_KEY == "YOUR_SUPABASE_SERVICE_KEY"):
                logger.warning("HeyGen/Supabase credentials not configured - skipping knowledge base update")
                return
            
            # Create knowledge updater and update the knowledge base
            async with HeyGenKnowledgeUpdater(
                heygen_api_key=HEYGEN_API_KEY,
                supabase_url=SUPABASE_URL,
                supabase_service_key=SUPABASE_SERVICE_KEY,
                knowledge_base_id=KNOWLEDGE_BASE_ID
            ) as updater:
                success = await updater.update_knowledge_with_conversation_history()
                
                if success:
                    logger.info("✅ HeyGen knowledge base updated successfully")
                else:
                    logger.warning("⚠️ Failed to update HeyGen knowledge base")
                    
        except Exception as e:
            logger.error(f"Error updating HeyGen knowledge base: {e}")
    
    def get_source_id(self, source_name: str) -> int:
        """Get the scene item ID for a source"""
        try:
            # Get current scene
            current_scene = self.client.get_current_program_scene()
            scene_name = current_scene.current_program_scene_name
            
            # Get scene items
            scene_items = self.client.get_scene_item_list(scene_name)
            
            for item in scene_items.scene_items:
                if item['sourceName'] == source_name:
                    return item['sceneItemId']
            
            raise ValueError(f"Source '{source_name}' not found in current scene")
        except Exception as e:
            logger.error(f"Error getting source ID: {e}")
            return 1  # Fallback

def main():
    controller = OBSController()
    
    # Connect to OBS
    if not controller.connect():
        print("Failed to connect to OBS. Make sure:")
        print("1. OBS Studio is running")
        print("2. WebSocket server is enabled (Tools > WebSocket Server Settings)")
        print(f"3. WebSocket is configured on port {OBS_PORT}")
        return
    
    print("🎥 OBS Hotkey Controller Started!")
    print(f"📹 Press {START_HOTKEY.upper()} to start recording sequence")
    print(f"⏹️  Press {STOP_HOTKEY.upper()} to stop recording sequence")
    print("❌ Press ESC to quit")
    print("\nListening for hotkeys...")
    
    try:
        # Register hotkey handlers
        keyboard.add_hotkey(START_HOTKEY, controller.start_recording_sequence)
        keyboard.add_hotkey(STOP_HOTKEY, controller.stop_recording_sequence)
        
        # Keep the script running
        keyboard.wait('esc')
        
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 Shutting down...")
        controller.disconnect()

if __name__ == "__main__":
    main() 