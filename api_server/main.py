from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import sys
import json
from pathlib import Path

# Add meta directory to path so we can import the modules
meta_path = Path(__file__).parent.parent / "meta"
sys.path.append(str(meta_path))

from assistant import get_reply
from mic_to_text import transcribe_audio
from profile_manager import profile_manager

app = FastAPI(title="RizzBot API", description="AI-powered rizz generator for dates")

# Add CORS middleware for Expo app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Expo app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "RizzBot API is running! 🎯"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "RizzBot API is ready"}

@app.post("/rizz")
async def get_rizz_response(audio_file: UploadFile = File(...)):
    """
    Process audio and return rizz response
    """
    try:
        # Log the incoming file details for debugging
        print(f"🎤 Received audio file: {audio_file.filename} ({audio_file.content_type})")
        
        # Validate file type - be more permissive for Expo audio files
        filename = audio_file.filename.lower() if audio_file.filename else ""
        content_type = audio_file.content_type.lower() if audio_file.content_type else ""
        
        # Accept any file that looks like audio or has no extension (Expo might not set filename properly)
        is_audio = (
            filename.endswith(('.wav', '.mp3', '.m4a', '.aac', '.m4v', '.mov')) or
            content_type.startswith('audio/') or
            'audio' in content_type or
            not filename or  # Accept files without extension
            filename == 'recording.wav'  # Accept Expo's default filename
        )
        
        if not is_audio:
            print(f"❌ Rejected file: {filename} ({content_type})")
            raise HTTPException(status_code=400, detail=f"Only audio files are supported. Got: {filename} ({content_type})")
        
        print(f"✅ Accepted audio file: {filename} ({content_type})")
        
        # Save uploaded audio to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            print(f"🎧 Transcribing audio file: {temp_file_path}")
            # Transcribe the audio
            transcript = transcribe_audio(temp_file_path)
            print(f"📝 Transcript: {transcript}")
            
            if not transcript or transcript.strip() == "":
                print("❌ No speech detected in audio")
                return {
                    "success": False,
                    "message": "No speech detected in audio",
                    "rizz": "I didn't catch that. Could you repeat?"
                }
            
            print(f"🤖 Generating rizz for: {transcript}")
            # Get rizz response using existing logic
            rizz_response = get_reply(transcript)
            print(f"🎯 Rizz generated: {rizz_response}")
            
            # Trigger glasses to speak the rizz
            try:
                rizz_file = Path(__file__).parent.parent / "meta" / "rizz_to_speak.txt"
                with open(rizz_file, 'w') as f:
                    f.write(rizz_response)
                print(f"🎤 Triggered glasses to speak: {rizz_response}")
            except Exception as speak_error:
                print(f"Warning: Could not trigger glasses speech: {speak_error}")
            
            return {
                "success": True,
                "transcript": transcript,
                "rizz": rizz_response,
                "message": "Rizz generated successfully!"
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        print(f"Error processing rizz request: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@app.get("/profiles")
async def get_profiles():
    """Get Ava's profile info (always)"""
    try:
        # Always get Ava's profile info
        profile_info = profile_manager.load_profile('416')  # Ava's contact ID
        
        if profile_info:
            return {
                "success": True,
                "current_profile": {
                    "name": profile_info.get('name', 'Ava'),
                    "phone_number": profile_info.get('phone_number', '416'),
                    "interests": profile_info.get('interests', [])[:3],
                    "personality": profile_info.get('personality', {}).get('traits', [])[:3]
                }
            }
        else:
            return {
                "success": False,
                "message": "Ava's profile not found"
            }
            
    except Exception as e:
        print(f"Error getting Ava's profile: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting Ava's profile: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 