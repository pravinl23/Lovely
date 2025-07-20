import openai
import json
import dotenv
import os
from profile_manager import profile_manager

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Error: OPENAI_API_KEY not found in environment variables")

# Set API key properly using the new config system
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def build_prompt(transcript):
    # Always load Ava's profile
    profile = profile_manager.load_profile('416')  # Ava's contact ID
    
    if not profile:
        return f"""
You're an AI assistant helping me on a date. The person just said: "{transcript}"

What is a charming, flirty, or witty one-liner I can say in response?
Keep it natural and conversational.
"""
    
    # Build comprehensive prompt using Ava's profile information
    name = profile.get('name', 'Ava')
    interests = ', '.join(profile.get('interests', []))
    personality = profile.get('personality', {})
    traits = ', '.join(personality.get('traits', []))
    facts = '\n- '.join(profile.get('facts_learned', [])[:5])  # Top 5 facts
    last_topics = ', '.join(profile.get('last_topics', [])[:3])  # Recent topics
    
    # Get unresolved topics for follow-up
    unresolved = profile.get('unresolved_topics', [])
    follow_ups = []
    for topic in unresolved[:2]:
        follow_ups.append(f"- {topic['question']}")
    follow_up_text = '\n'.join(follow_ups) if follow_ups else "No specific follow-ups needed."
    
    return f"""
You're an AI assistant helping me on a date with {name}.

PERSONALITY & INTERESTS:
- Name: {name}
- Interests: {interests}
- Personality traits: {traits}

KEY FACTS ABOUT THEM:
- {facts}

RECENT CONVERSATION TOPICS:
{last_topics if last_topics else "No recent topics"}

FOLLOW-UP OPPORTUNITIES:
{follow_up_text}

They just said: "{transcript}"

INSTRUCTIONS:
- Respond naturally and conversationally
- Be charming, witty, and engaging
- Reference their interests or recent topics when relevant
- Ask follow-up questions to learn more about them
- Keep the response concise (1-2 sentences)
- Match their energy and communication style
- Be authentic and avoid being overly scripted

Response:"""

def get_reply(transcript):
    """Get AI response using the current profile"""
    prompt = build_prompt(transcript)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful AI assistant that provides natural, engaging responses for real-time conversations. Be authentic, charming, and conversational."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=100
        )
        
        reply = response.choices[0].message.content.strip()
        
        # Log the conversation to Ava's profile (always)
        profile = profile_manager.load_profile('416')
        if profile:
            contact_id = '416'  # Always use Ava's contact ID
            profile_manager.add_conversation_log(contact_id, transcript, reply)
        
        return reply
        
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return "That's interesting! Tell me more about that."

def get_current_profile_info():
    """Get information about Ava's profile (always)"""
    profile = profile_manager.load_profile('416')  # Always load Ava
    if profile:
        return {
            'name': profile.get('name', 'Ava'),
            'phone_number': profile.get('phone_number', '416'),
            'interests': profile.get('interests', []),
            'personality': profile.get('personality', {}).get('traits', [])
        }
    return None
