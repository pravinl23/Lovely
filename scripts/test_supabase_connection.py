#!/usr/bin/env python3
"""
Test Supabase Connection Script

This script tests the connection to Supabase and verifies basic functionality.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config.settings import get_settings

def test_supabase_connection():
    """Test connection to Supabase"""
    settings = get_settings()
    
    print("🔍 Testing Supabase Connection...")
    print(f"📊 URL: {settings.supabase_url}")
    print(f"🔑 Anon Key: {settings.supabase_anon_key.get_secret_value()[:20]}...")
    print()
    
    try:
        # Test database connection
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Database connection successful: {row.test}")
            
            # Test table existence
            tables = ['users', 'contacts', 'messages', 'facts', 'outbound_replies', 'briefings', 'message_embeddings']
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"✅ Table {table}: {count} rows")
                except Exception as e:
                    print(f"❌ Table {table}: {e}")
            
            # Test pgvector extension
            try:
                result = conn.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
                if result.fetchone():
                    print("✅ pgvector extension is enabled")
                else:
                    print("❌ pgvector extension not found")
            except Exception as e:
                print(f"❌ pgvector check failed: {e}")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return True

def test_basic_operations():
    """Test basic CRUD operations"""
    settings = get_settings()
    
    print("\n🧪 Testing Basic Operations...")
    
    try:
        engine = create_engine(settings.database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test insert
        try:
            result = session.execute(text("""
                INSERT INTO users (email, hashed_password, whatsapp_phone_number_id, global_automation_enabled)
                VALUES ('test@example.com', 'test_hash', 'test_phone', false)
                RETURNING id
            """))
            user_id = result.fetchone()[0]
            session.commit()
            print(f"✅ Insert test successful - User ID: {user_id}")
            
            # Test select
            result = session.execute(text(f"SELECT email FROM users WHERE id = {user_id}"))
            email = result.fetchone()[0]
            print(f"✅ Select test successful - Email: {email}")
            
            # Test update
            session.execute(text(f"UPDATE users SET email = 'updated@example.com' WHERE id = {user_id}"))
            session.commit()
            print("✅ Update test successful")
            
            # Test delete
            session.execute(text(f"DELETE FROM users WHERE id = {user_id}"))
            session.commit()
            print("✅ Delete test successful")
            
        except Exception as e:
            print(f"❌ CRUD test failed: {e}")
            session.rollback()
            return False
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Basic operations test failed: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("Supabase Connection Test")
    print("=" * 30)
    
    # Test connection
    if not test_supabase_connection():
        print("\n❌ Connection test failed!")
        sys.exit(1)
    
    # Test basic operations
    if not test_basic_operations():
        print("\n❌ Basic operations test failed!")
        sys.exit(1)
    
    print("\n🎉 All tests passed! Supabase is ready to use.")

if __name__ == "__main__":
    main() 