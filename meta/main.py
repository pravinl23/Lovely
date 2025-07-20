from live_buffer import audio_stream, save_buffer_to_wav, stop_audio_stream
from assistant import get_reply, set_current_profile, list_available_profiles, create_new_profile, get_current_profile_name
from mic_to_text import transcribe_audio
from speak import speak
import threading
import time

def select_profile():
    """Let user select or create a profile"""
    profiles = list_available_profiles()
    
    if not profiles:
        print("No profiles found. Let's create your first one!")
        name = input("Enter the person's name: ").strip()
        if name:
            create_new_profile(name)
            return name
        else:
            return "Unknown"
    
    print("\nAvailable profiles:")
    for i, profile in enumerate(profiles, 1):
        print(f"{i}. {profile}")
    print(f"{len(profiles) + 1}. Create new profile")
    
    while True:
        try:
            choice = input(f"\nSelect profile (1-{len(profiles) + 1}): ").strip()
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(profiles):
                return profiles[choice_num - 1]
            elif choice_num == len(profiles) + 1:
                name = input("Enter the person's name: ").strip()
                if name:
                    create_new_profile(name)
                    return name
                else:
                    print("Invalid name, try again.")
            else:
                print("Invalid choice, try again.")
        except ValueError:
            print("Please enter a number.")

# Start background mic buffer thread
audio_thread = threading.Thread(target=audio_stream, daemon=True)
audio_thread.start()

# Give the audio stream time to initialize
time.sleep(1)

print("🎙️ Always listening... Let's set up your conversation partner.\n")

# Select profile
selected_profile = select_profile()
set_current_profile(selected_profile)

print(f"\n🎯 Ready! Talking to: {get_current_profile_name()}")
print("Press Enter to respond to last 10 seconds...\n")

try:
    while True:
        input("Tap to respond...\n")

        # Save last 10 seconds of mic input
        if save_buffer_to_wav():
            # Transcribe + respond
            her_line = transcribe_audio()
            print(f"💬 {get_current_profile_name()} said: {her_line}")

            response = get_reply(her_line)
            print(f"🤖 RizzBot says: {response}")

            speak(response)
        else:
            print("❌ No audio captured - try speaking louder")

except KeyboardInterrupt:
    print("\n🛑 Stopping audio buffer...")
    stop_audio_stream()
    print("👋 Goodbye!")
