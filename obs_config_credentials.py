"""
OBS Controller Configuration with HeyGen Integration
Copy this file and update with your actual credentials
"""

# =============================================================================
# OBS WebSocket Configuration
# =============================================================================
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = ""  # Set if you have a password configured in OBS

# =============================================================================
# Hotkey Configuration
# =============================================================================
START_HOTKEY = "f9"   # Key to start recording sequence
STOP_HOTKEY = "f10"   # Key to stop recording sequence

# =============================================================================
# OBS Source Configuration
# =============================================================================
BROWSER_SOURCE_NAME = "Browser"  # Must match exactly with your OBS source name

# =============================================================================
# Custom Commands
# =============================================================================
# These commands run before/after recording
START_COMMAND = ["echo", "Starting recording..."]  # Replace with your command
STOP_COMMAND = ["echo", "Recording stopped."]     # Replace with your command

# Example custom commands:
# START_COMMAND = ["curl", "-X", "POST", "http://localhost:3000/api/start-stream"]
# STOP_COMMAND = ["python", "cleanup_stream.py"]
# START_COMMAND = ["osascript", "-e", 'display notification "Stream started"']

# =============================================================================
# HeyGen API Configuration
# =============================================================================
# Get your HeyGen API key from: https://app.heygen.com/settings/api
HEYGEN_API_KEY = "YOUR_HEYGEN_API_KEY_HERE"  # Replace with your actual API key

# Your HeyGen Knowledge Base ID (specified in requirements)
KNOWLEDGE_BASE_ID = "bfa1e9e954c44662836e4b98dab05766"

# =============================================================================
# Supabase Configuration  
# =============================================================================
# Get these from your Supabase project settings
SUPABASE_URL = "https://your-project-id.supabase.co"  # Your Supabase project URL
SUPABASE_SERVICE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"  # Service role key (not anon key!)

# =============================================================================
# How to Get Your Credentials:
# =============================================================================

"""
🔑 HEYGEN API KEY:
1. Go to https://app.heygen.com/settings/api
2. Create a new API key
3. Copy the key and replace HEYGEN_API_KEY above

🗄️ SUPABASE CREDENTIALS:
1. Go to your Supabase project dashboard
2. Settings → API
3. Copy "Project URL" → replace SUPABASE_URL above  
4. Copy "service_role" key (NOT anon key) → replace SUPABASE_SERVICE_KEY above

⚠️ IMPORTANT SECURITY NOTES:
- Keep your API keys private and never commit them to git
- The service role key has full database access - handle with care
- Consider using environment variables instead of hardcoding keys

📋 KNOWLEDGE BASE SETUP:
- The knowledge base ID is already set to: bfa1e9e954c44662836e4b98dab05766
- This will be updated with your conversation history and personality prompt
- Make sure this knowledge base exists in your HeyGen account

🎯 OBS SOURCE SETUP:
- Make sure your browser source is named exactly: "Browser"
- Or update BROWSER_SOURCE_NAME to match your actual source name
- The source will be shown when recording starts, hidden when recording stops

🎹 HOTKEY SETUP:
- Default: F9 to start, F10 to stop
- Change START_HOTKEY and STOP_HOTKEY if you prefer different keys
- Requires accessibility permissions on macOS
""" 