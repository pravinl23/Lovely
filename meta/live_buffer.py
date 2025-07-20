import numpy as np
import sounddevice as sd
import threading
import time
import scipy.io.wavfile as wavfile
from collections import deque

SAMPLE_RATE = 16000
BUFFER_DURATION = 10
CHUNK_SIZE = 1024

# 10-second buffer
buffer = deque(maxlen=int(SAMPLE_RATE * BUFFER_DURATION))
stream_active = False

# Background stream that fills the buffer
def audio_stream():
    global stream_active
    
    def callback(indata, frames, time, status):
        if status:
            print(f"Audio callback status: {status}")
        # Convert to mono and add to buffer
        audio_chunk = indata[:, 0] if indata.ndim > 1 else indata
        buffer.extend(audio_chunk)
    
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE, 
            channels=1, 
            callback=callback, 
            blocksize=CHUNK_SIZE,
            dtype=np.float32
        ) as stream:
            stream_active = True
            print("Audio buffer started - listening...")
            while stream_active:
                time.sleep(0.1)
    except Exception as e:
        print(f"Audio stream error: {e}")

# Save current buffer to WAV
def save_buffer_to_wav(filename="temp.wav"):
    global buffer
    if len(buffer) == 0:
        print("Buffer is empty - no audio captured")
        return False
    
    # Convert buffer to numpy array
    audio_np = np.array(list(buffer), dtype=np.float32)
    
    # Normalize audio to prevent clipping
    if np.max(np.abs(audio_np)) > 0:
        audio_np = audio_np / np.max(np.abs(audio_np)) * 0.9
    
    # Convert to int16 for WAV file
    audio_int16 = (audio_np * 32767).astype(np.int16)
    
    # Save to WAV file
    wavfile.write(filename, SAMPLE_RATE, audio_int16)
    print(f"Saved {len(audio_np)/SAMPLE_RATE:.1f}s of audio to {filename}")
    return True

def stop_audio_stream():
    global stream_active
    stream_active = False
