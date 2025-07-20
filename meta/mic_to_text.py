# mic_to_text.py
import whisper
import pyaudio
import wave

model = whisper.load_model("base")

def record_audio(filename="temp.wav", seconds=10):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
    print("Recording...")
    frames = [stream.read(1024) for _ in range(int(44100 / 1024 * seconds))]
    stream.stop_stream(); stream.close(); p.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(frames))

def transcribe_audio(filename="temp.wav"):
    result = model.transcribe(filename)
    return result["text"]

