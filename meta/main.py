from mic_to_text import record_audio, transcribe_audio
from assistant import get_reply
from speak import speak

while True:
    input("Press Enter to record her for 10 seconds...\n")

    record_audio()

    her_line = transcribe_audio()
    print("She said:", her_line)

    response = get_reply(her_line)
    print("RizzBot says:", response)

    speak(response)
