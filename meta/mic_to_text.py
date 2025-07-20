# mic_to_text.py
import whisper

model = whisper.load_model("base")

def transcribe_audio(filename="temp.wav"):
    result = model.transcribe(filename)
    return result["text"]

