# OBS Hotkey Controller with HeyGen Integration

A Python script that automates OBS recording with custom commands, browser source control, and HeyGen knowledge base updates via global hotkeys.

## Features

- 🎯 **Global Hotkeys**: Works even when OBS isn't focused
- 🎬 **Recording Control**: Start/stop recording automatically  
- 👁️ **Source Visibility**: Show/hide browser sources
- ⚡ **Custom Commands**: Run any command before/after recording
- 🧠 **HeyGen Integration**: Automatically updates knowledge base with conversation history
- 📊 **Supabase Integration**: Pulls conversation context from your database
- 🔧 **Easy Configuration**: Simple config file setup

## Setup Instructions

### 1. Enable OBS WebSocket

1. Open OBS Studio
2. Go to **Tools** → **WebSocket Server Settings**
3. Check **"Enable WebSocket server"**
4. Set port to `4455` (default)
5. Set password if desired (optional)
6. Click **Apply**

### 2. Install Python Dependencies

```bash
pip install -r obs_requirements.txt
```

Or manually:
```bash
pip install obsws-python keyboard httpx
```

### 3. Configure API Credentials

**Set up HeyGen and Supabase credentials** in `obs_hotkey_controller.py`:

```python
# HeyGen API Configuration
HEYGEN_API_KEY = "your_heygen_api_key_here"
KNOWLEDGE_BASE_ID = "bfa1e9e954c44662836e4b98dab05766"

# Supabase Configuration  
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_SERVICE_KEY = "your_service_role_key_here"
```

**Get your credentials:**
- **HeyGen API Key**: Go to [HeyGen Settings > API](https://app.heygen.com/settings/api) and create a new key
- **Supabase URL & Key**: Go to your Supabase project → Settings → API

### 4. Configure the Script Settings

Edit the configuration section in `obs_hotkey_controller.py`:

```python
# Hotkey configuration
START_HOTKEY = "f9"     # Change to your preferred key
STOP_HOTKEY = "f10"     # Change to your preferred key

# Browser source name (must match exactly in OBS)
BROWSER_SOURCE_NAME = "Browser"  # Change to your source name

# Commands to run
START_COMMAND = ["echo", "Starting recording..."]  # Your start command
STOP_COMMAND = ["echo", "Recording stopped."]     # Your stop command
```

### 5. Run the Script

```bash
python obs_hotkey_controller.py
```

**Note**: On macOS/Linux, you may need to run with `sudo` for global hotkey access.

## Configuration Examples

### Basic Examples
```python
# Simple notification commands (macOS)
START_COMMAND = ["osascript", "-e", 'display notification "Recording started"']
STOP_COMMAND = ["osascript", "-e", 'display notification "Recording stopped"']

# Run Python scripts
START_COMMAND = ["python", "start_overlay.py"]
STOP_COMMAND = ["python", "cleanup.py"]

# API calls
START_COMMAND = ["curl", "-X", "POST", "http://localhost:3000/api/start"]
STOP_COMMAND = ["curl", "-X", "POST", "http://localhost:3000/api/stop"]
```

### Advanced Hotkey Combinations
```python
START_HOTKEY = "ctrl+shift+r"  # Ctrl+Shift+R
STOP_HOTKEY = "ctrl+shift+s"   # Ctrl+Shift+S
START_HOTKEY = "alt+f9"        # Alt+F9
```

### Multiple Browser Sources
If you need to control multiple sources, modify the script to include them:

```python
BROWSER_SOURCES = ["Browser Source 1", "Chat Overlay", "Alert Box"]
```

## Workflow

**When you press the START hotkey (F9 by default):**
1. ✅ Runs your custom start command
2. 🧠 **Updates HeyGen knowledge base** with conversation history from Supabase
3. 👁️ Makes browser source visible  
4. 🎬 Starts OBS recording

**When you press the STOP hotkey (F10 by default):**
1. 🛑 Stops OBS recording
2. 🙈 Hides browser source
3. ✅ Runs your custom stop command

## Troubleshooting

### "Failed to connect to OBS"
- Make sure OBS Studio is running
- Verify WebSocket server is enabled in OBS
- Check the port number (default: 4455)
- Verify password if you set one

### "Permission denied" or hotkeys not working
- **macOS/Linux**: Run with `sudo python obs_hotkey_controller.py`
- **Windows**: Run terminal as Administrator

### "Source not found"
- Check that `BROWSER_SOURCE_NAME` matches exactly with your OBS source name
- Source names are case-sensitive

### Hotkeys not working globally
- Make sure the `keyboard` library has proper permissions
- Try different hotkey combinations if conflicts exist

## Customization Ideas

- **Twitch Integration**: Start/stop stream alerts
- **Discord Bots**: Notify channels when recording
- **File Management**: Auto-organize recordings
- **Hardware Integration**: Control LED lights, send webhooks
- **Game Integration**: Trigger recordings based on game events

## Requirements

- Python 3.7+
- OBS Studio 28.0+ (with WebSocket support)
- `obsws-python` library
- `keyboard` library
- `httpx` library
- HeyGen API account with API key
- Supabase project with message data

## License

Free to use and modify for personal and commercial projects. 