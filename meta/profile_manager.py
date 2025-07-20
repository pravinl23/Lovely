import json
import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ProfileManager:
    """Manages loading and updating knowledge graphs for different contacts"""
    
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = profiles_dir
        self.current_profile = None
        
        # Get Supabase credentials from environment variables
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        # Validate environment variables
        if not self.supabase_url or self.supabase_url == "your_supabase_url_here":
            print("⚠️  Warning: SUPABASE_URL not configured in .env file")
            self.supabase_url = None
            
        if not self.supabase_key or self.supabase_key == "your_supabase_anon_key_here":
            print("⚠️  Warning: SUPABASE_ANON_KEY not configured in .env file")
            self.supabase_key = None
        
    def get_starred_contact(self) -> Optional[Dict[str, Any]]:
        """Get the currently starred contact from Supabase"""
        try:
            # This would normally fetch from Supabase
            # For now, we'll use a simple file-based approach
            settings_file = "current_starred.json"
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                    return data.get('starred_contact_id')
            return None
        except Exception as e:
            print(f"Error getting starred contact: {e}")
            return None
    
    def load_profile(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Load a specific contact's knowledge graph"""
        try:
            # Map contact IDs to profile files
            profile_mapping = {
                '647': 'bob.json',
                '416': 'ava.json', 
                '289': 'adam.json'
            }
            
            profile_file = profile_mapping.get(contact_id)
            if not profile_file:
                print(f"No profile mapping found for contact ID: {contact_id}")
                return None
            
            profile_path = os.path.join(self.profiles_dir, profile_file)
            if not os.path.exists(profile_path):
                print(f"Profile file not found: {profile_path}")
                return None
            
            with open(profile_path, 'r') as f:
                profile = json.load(f)
                self.current_profile = profile
                return profile
                
        except Exception as e:
            print(f"Error loading profile: {e}")
            return None
    
    def get_current_profile(self) -> Optional[Dict[str, Any]]:
        """Get the currently active profile (always Ava)"""
        if self.current_profile:
            return self.current_profile
        
        # Always load Ava's profile
        return self.load_profile('416')  # Always Ava
    
    def update_profile(self, contact_id: str, updates: Dict[str, Any]) -> bool:
        """Update a contact's knowledge graph with new information"""
        try:
            profile = self.load_profile(contact_id)
            if not profile:
                return False
            
            # Update the profile with new information
            for key, value in updates.items():
                if key in profile:
                    if isinstance(profile[key], list):
                        profile[key].extend(value if isinstance(value, list) else [value])
                    elif isinstance(profile[key], dict):
                        profile[key].update(value)
                    else:
                        profile[key] = value
            
            # Save the updated profile
            profile_mapping = {
                '647': 'bob.json',
                '416': 'ava.json', 
                '289': 'adam.json'
            }
            
            profile_file = profile_mapping.get(contact_id)
            if profile_file:
                profile_path = os.path.join(self.profiles_dir, profile_file)
                with open(profile_path, 'w') as f:
                    json.dump(profile, f, indent=2)
                
                # Update current profile if it's the active one
                if self.current_profile and self.current_profile.get('phone_number') == contact_id:
                    self.current_profile = profile
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
    
    def add_conversation_log(self, contact_id: str, transcript: str, response: str, context: str = ""):
        """Add a conversation log entry to the profile"""
        try:
            from datetime import datetime
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "transcript": transcript,
                "response": response,
                "context": context
            }
            
            # Load current profile
            profile = self.load_profile(contact_id)
            if not profile:
                return False
            
            # Initialize conversation_logs if it doesn't exist
            if 'conversation_logs' not in profile:
                profile['conversation_logs'] = []
            
            # Add the log entry
            profile['conversation_logs'].append(log_entry)
            
            # Keep only the last 50 entries
            if len(profile['conversation_logs']) > 50:
                profile['conversation_logs'] = profile['conversation_logs'][-50:]
            
            # Save the updated profile
            profile_mapping = {
                '647': 'bob.json',
                '416': 'ava.json', 
                '289': 'adam.json'
            }
            
            profile_file = profile_mapping.get(contact_id)
            if profile_file:
                profile_path = os.path.join(self.profiles_dir, profile_file)
                with open(profile_path, 'w') as f:
                    json.dump(profile, f, indent=2)
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error adding conversation log: {e}")
            return False
    
    def get_profile_summary(self, contact_id: str) -> str:
        """Get a summary of the profile for prompt building"""
        profile = self.load_profile(contact_id)
        if not profile:
            return "No profile information available."
        
        summary_parts = []
        
        # Basic info
        summary_parts.append(f"Name: {profile.get('name', 'Unknown')}")
        
        # Interests
        interests = profile.get('interests', [])
        if interests:
            summary_parts.append(f"Interests: {', '.join(interests)}")
        
        # Personality traits
        personality = profile.get('personality', {})
        traits = personality.get('traits', [])
        if traits:
            summary_parts.append(f"Personality: {', '.join(traits)}")
        
        # Facts learned
        facts = profile.get('facts_learned', [])
        if facts:
            summary_parts.append(f"Key facts: {', '.join(facts[:5])}")  # Limit to 5 facts
        
        # Last topics
        last_topics = profile.get('last_topics', [])
        if last_topics:
            summary_parts.append(f"Recent topics: {', '.join(last_topics)}")
        
        # Unresolved topics
        unresolved = profile.get('unresolved_topics', [])
        if unresolved:
            questions = [topic['question'] for topic in unresolved[:2]]
            summary_parts.append(f"Follow-up questions: {'; '.join(questions)}")
        
        return "\n".join(summary_parts)

# Global instance
profile_manager = ProfileManager() 