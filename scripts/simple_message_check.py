#!/usr/bin/env python3
"""
Simple Message Check Script

A basic script to check if messages are being stored in your database.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def simple_check():
    """Simple database check"""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("   Make sure your .env file exists and contains DATABASE_URL")
        return
    
    print(f"📊 Database URL: {database_url[:50]}...")
    print()
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('messages', 'contacts', 'users')
            """))
            tables = [row[0] for row in result.fetchall()]
            
            print("📋 Database Tables Found:")
            for table in ['messages', 'contacts', 'users']:
                status = "✅" if table in tables else "❌"
                print(f"   {status} {table}")
            print()
            
            if 'messages' not in tables:
                print("❌ Messages table not found - database may not be initialized")
                return
            
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
            
            # Check embeddings table
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM message_embeddings"))
                total_embeddings = result.scalar()
            except:
                total_embeddings = 0
            
            print("📊 Message Statistics:")
            print(f"   Total Messages: {total_messages}")
            print(f"   Recent Messages (1h): {recent_messages}")
            print(f"   Total Contacts: {total_contacts}")
            print(f"   Total Embeddings: {total_embeddings}")
            print()
            
            if total_messages > 0:
                print("✅ Messages are being stored successfully!")
                
                # Show a few recent messages
                result = conn.execute(text("""
                    SELECT m.text_content, m.timestamp, m.is_inbound, c.whatsapp_id
                    FROM messages m
                    JOIN contacts c ON m.contact_id = c.id
                    ORDER BY m.timestamp DESC
                    LIMIT 3
                """))
                
                recent = result.fetchall()
                if recent:
                    print("📨 Recent Messages:")
                    for msg in recent:
                        direction = "📥" if msg.is_inbound else "📤"
                        timestamp = msg.timestamp.strftime("%H:%M:%S")
                        content = msg.text_content or "[media message]"
                        if len(content) > 50:
                            content = content[:47] + "..."
                        print(f"   {direction} {timestamp} | {msg.whatsapp_id}: {content}")
            else:
                print("⚠️  No messages found - check your webhook configuration")
                print("   Make sure your WhatsApp webhook is properly configured")
                
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        print("   Check your DATABASE_URL and ensure the database is running")

if __name__ == "__main__":
    simple_check() 