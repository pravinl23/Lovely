"""
Example configuration for OBS Hotkey Controller
Copy this to obs_config.py and customize for your needs
"""

# OBS WebSocket settings
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = ""  # Leave empty if no password set

# Hotkey configuration (use keyboard module key names)
# Examples: 'f9', 'f10', 'ctrl+r', 'alt+s', 'shift+f1'
START_HOTKEY = "f9"
STOP_HOTKEY = "f10"

# Browser source name (must match exactly in OBS)
BROWSER_SOURCE_NAME = "Browser Source"

# Commands to execute
# Example commands:
START_COMMAND = ["echo", "Recording started"]
STOP_COMMAND = ["echo", "Recording stopped"]

# Real-world examples:
# START_COMMAND = ["python", "start_stream_overlay.py"]
# STOP_COMMAND = ["python", "cleanup_stream.py"]
# 
# START_COMMAND = ["curl", "-X", "POST", "http://localhost:3000/api/start"]
# STOP_COMMAND = ["curl", "-X", "POST", "http://localhost:3000/api/stop"]
#
# START_COMMAND = ["osascript", "-e", 'display notification "Recording started"']
# STOP_COMMAND = ["osascript", "-e", 'display notification "Recording stopped"'] 