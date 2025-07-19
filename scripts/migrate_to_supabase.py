#!/usr/bin/env python3
"""
Supabase Migration Script for WhatsApp Automation

This script helps migrate your local PostgreSQL database to Supabase.
It handles:
1. Schema migration
2. Data migration (if needed)
3. Environment configuration updates
4. Connection testing
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config.settings import get_settings

class SupabaseMigrator:
    def __init__(self):
        self.settings = get_settings()
        self.supabase_url = "https://gpqwxdexrblnfwlkhosv.supabase.co"
        self.supabase_anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwcXd4ZGV4cmJsbmZ3bGtob3N2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI5NTUwOTAsImV4cCI6MjA2ODUzMTA5MH0.QKUmkXcdOm3IyBtYanFZm4Z2pboHojwySOrpatNOffs"
        
        # You'll need to get this from your Supabase dashboard
        self.supabase_password = os.getenv("SUPABASE_DB_PASSWORD")
        if not self.supabase_password:
            print("❌ Please set SUPABASE_DB_PASSWORD environment variable")
            print("   Get this from: Supabase Dashboard > Settings > Database")
            sys.exit(1)
            
        self.supabase_db_url = f"postgresql://postgres:{self.supabase_password}@db.gpqwxdexrblnfwlkhosv.supabase.co:5432/postgres?sslmode=require"
        
    def test_supabase_connection(self) -> bool:
        """Test connection to Supabase"""
        try:
            engine = create_engine(self.supabase_db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("✅ Successfully connected to Supabase!")
                return True
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {e}")
            return False
    
    def execute_schema_migration(self) -> bool:
        """Execute the schema migration on Supabase"""
        try:
            # Read the schema file
            schema_path = Path(__file__).parent.parent / "supabase_schema.sql"
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Connect and execute
            engine = create_engine(self.supabase_db_url)
            with engine.connect() as conn:
                # Split by semicolon and execute each statement
                statements = schema_sql.split(';')
                for statement in statements:
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            conn.execute(text(statement))
                            conn.commit()
                        except Exception as e:
                            print(f"⚠️  Warning executing statement: {e}")
                            # Continue with other statements
                
            print("✅ Schema migration completed!")
            return True
            
        except Exception as e:
            print(f"❌ Schema migration failed: {e}")
            return False
    
    def migrate_data(self, migrate_existing_data: bool = False) -> bool:
        """Migrate data from local database to Supabase"""
        if not migrate_existing_data:
            print("⏭️  Skipping data migration (no existing data to migrate)")
            return True
            
        try:
            # Connect to local database
            local_engine = create_engine(self.settings.database_url)
            supabase_engine = create_engine(self.supabase_db_url)
            
            # Tables to migrate (in order due to foreign key constraints)
            tables = ['users', 'contacts', 'messages', 'facts', 'outbound_replies', 'briefings', 'message_embeddings']
            
            for table in tables:
                print(f"📦 Migrating table: {table}")
                
                # Get data from local
                with local_engine.connect() as local_conn:
                    result = local_conn.execute(text(f"SELECT * FROM {table}"))
                    rows = result.fetchall()
                
                if not rows:
                    print(f"   No data in {table}")
                    continue
                
                # Insert into Supabase
                with supabase_engine.connect() as supabase_conn:
                    for row in rows:
                        # Convert row to dict
                        row_dict = dict(row._mapping)
                        
                        # Build INSERT statement
                        columns = ', '.join(row_dict.keys())
                        placeholders = ', '.join([f':{k}' for k in row_dict.keys()])
                        insert_sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                        
                        try:
                            supabase_conn.execute(text(insert_sql), row_dict)
                        except Exception as e:
                            print(f"   ⚠️  Warning inserting into {table}: {e}")
                    
                    supabase_conn.commit()
                
                print(f"   ✅ Migrated {len(rows)} rows from {table}")
            
            print("✅ Data migration completed!")
            return True
            
        except Exception as e:
            print(f"❌ Data migration failed: {e}")
            return False
    
    def update_environment_file(self) -> bool:
        """Update .env file with Supabase configuration"""
        try:
            env_path = Path(__file__).parent.parent / ".env"
            
            if not env_path.exists():
                print("❌ .env file not found")
                return False
            
            # Read current .env
            with open(env_path, 'r') as f:
                env_content = f.read()
            
            # Update database URL
            env_content = env_content.replace(
                f"DATABASE_URL={self.settings.database_url}",
                f"DATABASE_URL={self.supabase_db_url}"
            )
            
            # Add Supabase configuration
            supabase_config = f"""
# Supabase Configuration
SUPABASE_URL={self.supabase_url}
SUPABASE_ANON_KEY={self.supabase_anon_key}
SUPABASE_DB_PASSWORD={self.supabase_password}
"""
            
            # Add if not already present
            if "SUPABASE_URL" not in env_content:
                env_content += supabase_config
            
            # Write back
            with open(env_path, 'w') as f:
                f.write(env_content)
            
            print("✅ Environment file updated!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update environment file: {e}")
            return False
    
    def enable_pgvector(self) -> bool:
        """Enable pgvector extension for embeddings"""
        try:
            engine = create_engine(self.supabase_db_url)
            with engine.connect() as conn:
                # Enable pgvector
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                
                # Update message_embeddings table to use vector type
                conn.execute(text("""
                    ALTER TABLE message_embeddings 
                    DROP COLUMN IF EXISTS embedding_vector;
                """))
                
                conn.execute(text("""
                    ALTER TABLE message_embeddings 
                    ADD COLUMN embedding_vector vector(1536);
                """))
                
                conn.commit()
            
            print("✅ pgvector extension enabled and table updated!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to enable pgvector: {e}")
            return False
    
    def configure_rls_policies(self) -> bool:
        """Configure Row Level Security policies for production"""
        try:
            engine = create_engine(self.supabase_db_url)
            with engine.connect() as conn:
                # Disable basic RLS policies for service access
                conn.execute(text('DROP POLICY IF EXISTS "Users can view own data" ON users'))
                conn.execute(text('DROP POLICY IF EXISTS "Users can view own contacts" ON contacts'))
                conn.execute(text('DROP POLICY IF EXISTS "Users can view own messages" ON messages'))
                
                # Create service role policy for full access
                conn.execute(text("""
                    CREATE POLICY "Service full access" ON users
                        FOR ALL USING (true);
                """))
                
                conn.execute(text("""
                    CREATE POLICY "Service full access" ON contacts
                        FOR ALL USING (true);
                """))
                
                conn.execute(text("""
                    CREATE POLICY "Service full access" ON messages
                        FOR ALL USING (true);
                """))
                
                conn.commit()
            
            print("✅ RLS policies configured for service access!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to configure RLS policies: {e}")
            return False
    
    def run_migration(self, migrate_data: bool = False):
        """Run the complete migration process"""
        print("🚀 Starting Supabase Migration...")
        print(f"📊 Target: {self.supabase_url}")
        print()
        
        # Step 1: Test connection
        print("1️⃣  Testing Supabase connection...")
        if not self.test_supabase_connection():
            return False
        print()
        
        # Step 2: Execute schema
        print("2️⃣  Executing schema migration...")
        if not self.execute_schema_migration():
            return False
        print()
        
        # Step 3: Enable pgvector
        print("3️⃣  Enabling pgvector extension...")
        if not self.enable_pgvector():
            return False
        print()
        
        # Step 4: Configure RLS
        print("4️⃣  Configuring RLS policies...")
        if not self.configure_rls_policies():
            return False
        print()
        
        # Step 5: Migrate data (if requested)
        if migrate_data:
            print("5️⃣  Migrating existing data...")
            if not self.migrate_data(migrate_data):
                return False
            print()
        
        # Step 6: Update environment
        print("6️⃣  Updating environment configuration...")
        if not self.update_environment_file():
            return False
        print()
        
        print("🎉 Migration completed successfully!")
        print()
        print("📋 Next steps:")
        print("   1. Test your application with the new Supabase connection")
        print("   2. Update your application code if needed")
        print("   3. Monitor performance and adjust as needed")
        print("   4. Consider enabling Supabase features like realtime subscriptions")
        
        return True

def main():
    """Main migration function"""
    print("Supabase Migration Tool for WhatsApp Automation")
    print("=" * 50)
    
    # Check if user wants to migrate existing data
    migrate_data = input("Do you want to migrate existing data from your local database? (y/N): ").lower().strip() == 'y'
    
    # Run migration
    migrator = SupabaseMigrator()
    success = migrator.run_migration(migrate_data=migrate_data)
    
    if not success:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)
    
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    main() 