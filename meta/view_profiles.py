#!/usr/bin/env python3
"""
Profile Viewer - View and manage knowledge graph profiles
"""

import json
import os
from knowledge_manager import knowledge_manager

def view_profile(name: str):
    """View a specific profile in detail"""
    profile = knowledge_manager.load_profile(name)
    if not profile:
        print(f"❌ Profile '{name}' not found")
        return
    
    print(f"\n📋 Profile: {profile['name']}")
    print(f"📅 Created: {profile['created_at']}")
    print(f"🔄 Last Updated: {profile['last_updated']}")
    print(f"💬 Conversations: {profile['conversation_count']}")
    print(f"💕 Relationship Stage: {profile['relationship_stage']}")
    
    print(f"\n🎯 Interests: {', '.join(profile['interests']) if profile['interests'] else 'None'}")
    print(f"👤 Personality: {', '.join(profile['personality_traits']) if profile['personality_traits'] else 'None'}")
    print(f"📚 Facts: {', '.join(profile['facts_learned']) if profile['facts_learned'] else 'None'}")
    print(f"💭 Recent Topics: {', '.join(profile['last_topics']) if profile['last_topics'] else 'None'}")
    
    print(f"\n📱 WhatsApp Messages: {len(profile['whatsapp_messages'])}")
    print(f"🎤 Voice Conversations: {len(profile['voice_conversations'])}")
    
    # Show recent messages
    if profile['whatsapp_messages']:
        print(f"\n📱 Recent WhatsApp Messages:")
        for msg in profile['whatsapp_messages'][-3:]:  # Last 3 messages
            direction = "📥" if msg['direction'] == 'from_contact' else "📤"
            print(f"  {direction} {msg['content'][:50]}...")
    
    if profile['voice_conversations']:
        print(f"\n🎤 Recent Voice Conversations:")
        for conv in profile['voice_conversations'][-3:]:  # Last 3 conversations
            print(f"  💬 {conv['transcript'][:50]}...")
            print(f"  🤖 {conv['ai_response'][:50]}...")

def list_profiles():
    """List all profiles with basic info"""
    profiles = knowledge_manager.list_profiles()
    
    if not profiles:
        print("📭 No profiles found")
        return
    
    print(f"\n📋 Available Profiles ({len(profiles)}):")
    print("-" * 50)
    
    for name in profiles:
        profile = knowledge_manager.load_profile(name)
        if profile:
            print(f"👤 {name}")
            print(f"   💬 {profile['conversation_count']} conversations")
            print(f"   💕 {profile['relationship_stage']}")
            print(f"   🎯 {len(profile['interests'])} interests")
            print(f"   📚 {len(profile['facts_learned'])} facts")
            print()

def main():
    """Main profile viewer interface"""
    while True:
        print("\n🔍 Knowledge Graph Profile Viewer")
        print("1. List all profiles")
        print("2. View specific profile")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            list_profiles()
        elif choice == "2":
            profiles = knowledge_manager.list_profiles()
            if not profiles:
                print("❌ No profiles available")
                continue
                
            print("\nAvailable profiles:")
            for i, name in enumerate(profiles, 1):
                print(f"{i}. {name}")
            
            try:
                profile_choice = int(input(f"\nSelect profile (1-{len(profiles)}): ")) - 1
                if 0 <= profile_choice < len(profiles):
                    view_profile(profiles[profile_choice])
                else:
                    print("❌ Invalid choice")
            except ValueError:
                print("❌ Please enter a number")
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main() 