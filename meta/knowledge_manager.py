import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import openai
import dotenv

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("Error: OPENAI_API_KEY not found in environment variables")

# Initialize OpenAI client
try:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"Warning: Could not initialize OpenAI client: {e}")
    client = None

class KnowledgeGraphManager:
    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = knowledge_dir
        os.makedirs(knowledge_dir, exist_ok=True)
        
    def get_profile_path(self, name: str) -> str:
        """Get the file path for a person's knowledge graph"""
        # Clean name for filename
        clean_name = name.lower().replace(" ", "_").replace("-", "_")
        return os.path.join(self.knowledge_dir, f"{clean_name}_knowledge.json")
    
    def create_profile(self, name: str, initial_info: Dict = None) -> Dict:
        """Create a new knowledge graph profile"""
        profile = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "interests": [],
            "personality_traits": [],
            "conversation_history": [],
            "preferences": {
                "tone": "neutral",
                "topics": [],
                "communication_style": "unknown"
            },
            "facts_learned": [],
            "last_topics": [],
            "relationship_stage": "new",
            "conversation_count": 0,
            "whatsapp_messages": [],
            "voice_conversations": []
        }
        
        if initial_info:
            profile.update(initial_info)
            
        self.save_profile(name, profile)
        return profile
    
    def load_profile(self, name: str) -> Optional[Dict]:
        """Load a person's knowledge graph"""
        profile_path = self.get_profile_path(name)
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def save_profile(self, name: str, profile: Dict):
        """Save a person's knowledge graph"""
        profile_path = self.get_profile_path(name)
        profile["last_updated"] = datetime.now().isoformat()
        
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
    
    def list_profiles(self) -> List[str]:
        """List all available profiles"""
        profiles = []
        for filename in os.listdir(self.knowledge_dir):
            if filename.endswith("_knowledge.json"):
                # Extract name from filename
                name = filename.replace("_knowledge.json", "").replace("_", " ").title()
                profiles.append(name)
        return profiles
    
    def update_from_whatsapp(self, name: str, message: str, is_from_contact: bool = True):
        """Update knowledge graph from WhatsApp message"""
        profile = self.load_profile(name)
        if not profile:
            profile = self.create_profile(name)
        
        # Add message to history
        message_entry = {
            "timestamp": datetime.now().isoformat(),
            "content": message,
            "source": "whatsapp",
            "direction": "from_contact" if is_from_contact else "to_contact"
        }
        profile["whatsapp_messages"].append(message_entry)
        
        # Extract facts and insights using AI
        if is_from_contact:
            self._extract_insights_from_message(profile, message)
        
        profile["conversation_count"] += 1
        self.save_profile(name, profile)
    
    def update_from_voice(self, name: str, transcript: str, ai_response: str):
        """Update knowledge graph from voice conversation"""
        profile = self.load_profile(name)
        if not profile:
            profile = self.create_profile(name)
        
        # Add conversation to history
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "transcript": transcript,
            "ai_response": ai_response,
            "source": "voice"
        }
        profile["voice_conversations"].append(conversation_entry)
        
        # Extract insights from the conversation
        self._extract_insights_from_message(profile, transcript)
        
        profile["conversation_count"] += 1
        self.save_profile(name, profile)
    
    def _extract_insights_from_message(self, profile: Dict, message: str):
        """Use AI to extract insights from a message"""
        if client is None:
            print("Warning: OpenAI client not available, skipping insight extraction")
            return
            
        try:
            prompt = f"""
            Analyze this message from {profile['name']}: "{message}"
            
            Extract and update the following information (return as JSON):
            - new_interests: List of interests mentioned
            - new_personality_traits: Personality traits shown
            - new_facts: Facts learned about the person
            - new_topics: Topics discussed
            - relationship_insights: Any insights about relationship stage
            
            Current profile context:
            - Interests: {profile['interests']}
            - Personality: {profile['personality_traits']}
            - Facts: {profile['facts_learned']}
            - Last topics: {profile['last_topics']}
            
            Only return new information that's not already in the profile.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            insights = json.loads(response.choices[0].message.content)
            
            # Update profile with new insights
            if insights.get("new_interests"):
                profile["interests"].extend(insights["new_interests"])
                profile["interests"] = list(set(profile["interests"]))  # Remove duplicates
            
            if insights.get("new_personality_traits"):
                profile["personality_traits"].extend(insights["new_personality_traits"])
                profile["personality_traits"] = list(set(profile["personality_traits"]))
            
            if insights.get("new_facts"):
                profile["facts_learned"].extend(insights["new_facts"])
                profile["facts_learned"] = list(set(profile["facts_learned"]))
            
            if insights.get("new_topics"):
                profile["last_topics"].extend(insights["new_topics"])
                profile["last_topics"] = profile["last_topics"][-5:]  # Keep last 5 topics
            
            if insights.get("relationship_insights"):
                # Could update relationship stage based on insights
                pass
                
        except Exception as e:
            print(f"Error extracting insights: {e}")
    
    def get_conversation_context(self, name: str) -> str:
        """Get formatted context for AI prompts"""
        profile = self.load_profile(name)
        if not profile:
            return f"New person: {name}"
        
        context_parts = [
            f"Name: {profile['name']}",
            f"Interests: {', '.join(profile['interests'])}",
            f"Personality: {', '.join(profile['personality_traits'])}",
            f"Facts: {', '.join(profile['facts_learned'])}",
            f"Recent topics: {', '.join(profile['last_topics'])}",
            f"Relationship stage: {profile['relationship_stage']}"
        ]
        
        return "\n".join(context_parts)

# Global instance
knowledge_manager = KnowledgeGraphManager() 