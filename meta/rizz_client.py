import requests
import time
import json
from speak import speak
import threading
import os
from dotenv import load_dotenv

load_dotenv()

class RizzClient:
    """Client that receives rizz text and speaks it through glasses"""
    
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.running = False
        self.check_thread = None
        
    def start_listening(self):
        """Start listening for rizz responses"""
        self.running = True
        self.check_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.check_thread.start()
        print("🎧 RizzClient started - listening for responses...")
        
    def stop_listening(self):
        """Stop listening for rizz responses"""
        self.running = False
        if self.check_thread:
            self.check_thread.join()
        print("🛑 RizzClient stopped")
        
    def _listen_loop(self):
        """Main listening loop - checks for new rizz responses"""
        while self.running:
            try:
                # Check if there's a new rizz response to speak
                # For now, we'll use a simple file-based approach
                rizz_file = "rizz_to_speak.txt"
                
                if os.path.exists(rizz_file):
                    with open(rizz_file, 'r') as f:
                        rizz_text = f.read().strip()
                    
                    if rizz_text:
                        print(f"🎤 Speaking: {rizz_text}")
                        speak(rizz_text)
                        
                        # Clear the file after speaking
                        os.remove(rizz_file)
                        
            except Exception as e:
                print(f"Error in rizz listening loop: {e}")
                
            time.sleep(0.5)  # Check every 500ms
    
    def speak_rizz(self, rizz_text):
        """Immediately speak the given rizz text"""
        try:
            print(f"🎤 Speaking: {rizz_text}")
            speak(rizz_text)
        except Exception as e:
            print(f"Error speaking rizz: {e}")

# Global instance
rizz_client = RizzClient()

def start_rizz_client():
    """Start the rizz client"""
    rizz_client.start_listening()

def stop_rizz_client():
    """Stop the rizz client"""
    rizz_client.stop_listening()

def speak_rizz(rizz_text):
    """Speak rizz text immediately"""
    rizz_client.speak_rizz(rizz_text)

if __name__ == "__main__":
    print("🎧 Starting RizzClient...")
    start_rizz_client()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping RizzClient...")
        stop_rizz_client() 