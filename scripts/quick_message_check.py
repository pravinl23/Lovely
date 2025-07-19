#!/usr/bin/env python3
"""
Quick Message Check Script

A fast script to quickly check if messages are being stored in your database.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text

# Add paths for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import get_settings

def quick_check():
    """Quick database check"""
    settings = get_settings()
    
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            # Check total messages
            result = conn.execute(text("SELECT COUNT(*) FROM messages"))
            total_messages = result.scalar()
            
            # Check recent messages (last hour)
            result = conn.execute(text("""
                SELECT COUNT(*) FROM messages 
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            """))
            recent_messages = result.scalar()
            
            # Check if any contacts exist
            result = conn.execute(text("SELECT COUNT(*) FROM contacts"))
            total_contacts = result.scalar()
            
            # Check embeddings
            result = conn.execute(text("SELECT COUNT(*) FROM message_embeddings"))
            total_embeddings = result.scalar()
            
            print("📊 Quick Database Check:")
            print(f"   Total Messages: {total_messages}")
            print(f"   Recent Messages (1h): {recent_messages}")
            print(f"   Total Contacts: {total_contacts}")
            print(f"   Total Embeddings: {total_embeddings}")
            
            if total_messages > 0:
                print("✅ Messages are being stored successfully!")
            else:
                print("⚠️  No messages found - check your webhook configuration")
                
    except Exception as e:
        print(f"❌ Database check failed: {e}")

if __name__ == "__main__":
    quick_check() 