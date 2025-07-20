import openai
import json
import dotenv
import os
from knowledge_manager import knowledge_manager

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Error: OPENAI_API_KEY not found in environment variables")

# Set API key properly using the new config system
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Default profile name - can be changed dynamically
current_profile_name = "Unknown"

def set_current_profile(name: str):
    """Set the current person being talked to"""
    global current_profile_name
    current_profile_name = name
    print(f"🎯 Now talking to: {name}")

def get_current_profile_name() -> str:
    """Get the current profile name"""
    return current_profile_name

def build_prompt(transcript: str) -> str:
    """Build AI prompt with knowledge graph context"""
    # Get context from knowledge manager
    context = knowledge_manager.get_conversation_context(current_profile_name)
    
    prompt = f"""
You're an AI assistant helping me on a date/conversation with someone.

{context}

They just said: "{transcript}"

What is a charming, flirty, or witty one-liner I can say in response? 
Keep it natural and conversational, not too long.
"""
    return prompt

def get_reply(transcript: str) -> str:
    """Get AI response and update knowledge graph"""
    prompt = build_prompt(transcript)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    )
    
    ai_response = response.choices[0].message.content
    
    # Update knowledge graph with this conversation
    knowledge_manager.update_from_voice(current_profile_name, transcript, ai_response)
    
    return ai_response

def list_available_profiles() -> list:
    """List all available knowledge graph profiles"""
    return knowledge_manager.list_profiles()

def create_new_profile(name: str, initial_info: dict = None) -> dict:
    """Create a new knowledge graph profile"""
    return knowledge_manager.create_profile(name, initial_info)
