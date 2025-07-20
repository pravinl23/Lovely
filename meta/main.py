from live_buffer import audio_stream, save_buffer_to_wav, stop_audio_stream
from assistant import get_reply, get_current_profile_info
from mic_to_text import transcribe_audio
from speak import speak
import threading
import time

# Start background mic buffer thread
audio_thread = threading.Thread(target=audio_stream, daemon=True)
audio_thread.start()

# Give the audio stream time to initialize
time.sleep(1)

print("🎤 Always listening... Press Enter to trigger RizzBot.\n")

# Show current active profile
profile_info = get_current_profile_info()
if profile_info:
    print(f"👤 Active Profile: {profile_info['name']} ({profile_info['phone_number']})")
    print(f"🎯 Interests: {', '.join(profile_info['interests'][:3])}")
    print(f"✨ Personality: {', '.join(profile_info['personality'][:3])}")
else:
    print("⚠️  No active profile found - using default settings")
print()

try:
    while True:
        input("Tap to respond to last 10 seconds...\n")

        # Save last 10 seconds of mic input
        if save_buffer_to_wav():
            # Transcribe + respond
            her_line = transcribe_audio()
            print(f"🎧 They said: {her_line}")

            response = get_reply(her_line)
            print(f"🤖 RizzBot says: {response}")

            speak(response)
        else:
            print("❌ No audio captured - try speaking louder")

except KeyboardInterrupt:
    print("\n🛑 Stopping audio buffer...")
    stop_audio_stream()
    print("👋 Goodbye!")
