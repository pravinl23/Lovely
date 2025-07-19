#!/usr/bin/env python3
"""
Check Both Databases Script

This script checks both your local PostgreSQL and Supabase to see where messages are being stored.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_database(database_url, name):
    """Check a specific database"""
    print(f"🔍 Checking {name}...")
    print(f"📊 URL: {database_url[:50]}...")
    
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
            
            print(f"📋 Tables in {name}:")
            for table in ['messages', 'contacts', 'users']:
                status = "✅" if table in tables else "❌"
                print(f"   {status} {table}")
            
            if 'messages' not in tables:
                print(f"   ❌ No messages table in {name}")
                return None
            
            # Check message count
            result = conn.execute(text("SELECT COUNT(*) FROM messages"))
            total_messages = result.scalar()
            
            # Check recent messages
            result = conn.execute(text("""
                SELECT COUNT(*) FROM messages 
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
            """))
            recent_messages = result.scalar()
            
            print(f"📊 {name} Statistics:")
            print(f"   Total Messages: {total_messages}")
            print(f"   Recent Messages (1h): {recent_messages}")
            
            if total_messages > 0:
                # Show a recent message
                result = conn.execute(text("""
                    SELECT text_content, timestamp, is_inbound
                    FROM messages
                    ORDER BY timestamp DESC
                    LIMIT 1
                """))
                recent = result.fetchone()
                if recent:
                    direction = "📥" if recent.is_inbound else "📤"
                    timestamp = recent.timestamp.strftime("%H:%M:%S")
                    content = recent.text_content or "[media message]"
                    if len(content) > 40:
                        content = content[:37] + "..."
                    print(f"   Latest: {direction} {timestamp} - {content}")
            
            print()
            return total_messages
            
    except Exception as e:
        print(f"❌ Error checking {name}: {e}")
        print()
        return None

def main():
    """Check both databases"""
    print("Database Comparison Check")
    print("=" * 40)
    print()
    
    # Get database URLs
    local_db_url = os.getenv("DATABASE_URL")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not local_db_url:
        print("❌ DATABASE_URL not found in .env file")
        return
    
    if not supabase_url or not supabase_anon_key:
        print("⚠️  Supabase credentials not found in .env file")
        print("   Add SUPABASE_URL and SUPABASE_ANON_KEY to your .env file")
        return
    
    # Check local database
    local_messages = check_database(local_db_url, "Local PostgreSQL")
    
    # Check Supabase (using direct connection)
    # Note: This requires the database password from Supabase dashboard
    supabase_password = os.getenv("SUPABASE_DB_PASSWORD")
    if supabase_password:
        supabase_db_url = f"postgresql://postgres:{supabase_password}@db.gpqwxdexrblnfwlkhosv.supabase.co:5432/postgres?sslmode=require"
        supabase_messages = check_database(supabase_db_url, "Supabase")
    else:
        print("⚠️  SUPABASE_DB_PASSWORD not found")
        print("   Get it from: Supabase Dashboard > Settings > Database")
        print("   Then run: export SUPABASE_DB_PASSWORD='your_password'")
        supabase_messages = None
    
    # Summary
    print("📋 Summary:")
    if local_messages is not None:
        print(f"   Local PostgreSQL: {local_messages} messages")
    else:
        print("   Local PostgreSQL: ❌ Error or no messages table")
    
    if supabase_messages is not None:
        print(f"   Supabase: {supabase_messages} messages")
    else:
        print("   Supabase: ❌ Error or no messages table")
    
    print()
    
    if local_messages and local_messages > 0 and (supabase_messages is None or supabase_messages == 0):
        print("🎯 Current Status: Messages are stored in LOCAL database only")
        print("   To migrate to Supabase, run: python scripts/migrate_to_supabase.py")
    elif supabase_messages and supabase_messages > 0:
        print("✅ Messages are being stored in Supabase!")
    else:
        print("⚠️  No messages found in either database")

if __name__ == "__main__":
    main() 