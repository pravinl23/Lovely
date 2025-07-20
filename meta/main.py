from live_buffer import audio_stream, save_buffer_to_wav, stop_audio_stream
from assistant import get_reply
from mic_to_text import transcribe_audio
from speak import speak
import threading
import time

# Start background mic buffer thread
audio_thread = threading.Thread(target=audio_stream, daemon=True)
audio_thread.start()

# Give the audio stream time to initialize
time.sleep(1)

print("Always listening... Press Enter to trigger RizzBot.\n")

try:
    while True:
        input("Tap to respond to last 10 seconds...\n")

        # Save last 10 seconds of mic input
        if save_buffer_to_wav():
            # Transcribe + respond
            her_line = transcribe_audio()
            print("She said:", her_line)

            response = get_reply(her_line)
            print("RizzBot says:", response)

            speak(response)
        else:
            print("No audio captured - try speaking louder")

except KeyboardInterrupt:
    print("\nStopping audio buffer...")
    stop_audio_stream()
    print("Goodbye!")
