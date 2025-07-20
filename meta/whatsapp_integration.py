import json
import os
from knowledge_manager import knowledge_manager

def update_knowledge_from_whatsapp(contact_name: str, message: str, is_from_contact: bool = True):
    """
    Update knowledge graph from WhatsApp message
    This can be called from your WhatsApp automation system
    """
    try:
        knowledge_manager.update_from_whatsapp(contact_name, message, is_from_contact)
        print(f"✅ Updated knowledge graph for {contact_name}")
        return True
    except Exception as e:
        print(f"❌ Error updating knowledge graph: {e}")
        return False

def get_contact_knowledge_context(contact_name: str) -> str:
    """
    Get knowledge context for a contact
    This can be used in your WhatsApp automation to provide context to GPT
    """
    return knowledge_manager.get_conversation_context(contact_name)

def list_all_profiles() -> list:
    """List all available knowledge graph profiles"""
    return knowledge_manager.list_profiles()

def create_profile_from_whatsapp(contact_name: str, initial_message: str = None):
    """
    Create a new profile from WhatsApp contact
    """
    profile = knowledge_manager.create_profile(contact_name)
    
    if initial_message:
        knowledge_manager.update_from_whatsapp(contact_name, initial_message, True)
    
    return profile

# Example usage for WhatsApp automation integration
if __name__ == "__main__":
    # Example: When you receive a WhatsApp message
    contact_name = "Anna"
    message = "Hey! I love hiking and just got back from a trip to Portugal"
    
    # Update knowledge graph
    update_knowledge_from_whatsapp(contact_name, message, True)
    
    # Get context for AI response
    context = get_contact_knowledge_context(contact_name)
    print(f"Context for {contact_name}:")
    print(context) 