# Supabase Migration Guide

## 📋 Prerequisites

1. Create a Supabase account at https://supabase.com
2. Create a new project
3. Note your project URL and anon key

## 🚀 Migration Steps

### 1. Execute SQL Schema

1. Go to your Supabase Dashboard
2. Navigate to **SQL Editor**
3. Copy the entire contents of `supabase_schema.sql`
4. Paste and run it
5. Verify all tables are created under **Table Editor**

### 2. Update Environment Variables

Update your `.env` file:

```bash
# Old PostgreSQL connection
# DATABASE_URL=postgresql://user:password@localhost:5432/lovely

# New Supabase connection
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Optional: Add Supabase-specific vars
SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
SUPABASE_ANON_KEY=[YOUR-ANON-KEY]
```

### 3. Update Your Code

#### Option A: No Code Changes (Recommended)
Since Supabase is PostgreSQL-compatible, your SQLAlchemy code should work as-is with just the new `DATABASE_URL`.

#### Option B: Use Supabase Client (Optional)
If you want to use Supabase's additional features:

```bash
pip install supabase
```

### 4. Enable pgvector (For Embeddings)

In Supabase SQL Editor:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Update message_embeddings table to use vector type
ALTER TABLE message_embeddings 
DROP COLUMN embedding_vector;

ALTER TABLE message_embeddings 
ADD COLUMN embedding_vector vector(1536); -- Adjust dimension as needed
```

### 5. Configure Row Level Security (RLS)

For production, configure proper RLS policies:

```sql
-- Disable the basic RLS policies from the schema
DROP POLICY IF EXISTS "Users can view own data" ON users;
DROP POLICY IF EXISTS "Users can view own contacts" ON contacts;
DROP POLICY IF EXISTS "Users can view own messages" ON messages;

-- Create more specific policies based on your auth approach
-- Example: If using API keys for service access
CREATE POLICY "Service full access" ON users
    FOR ALL USING (
        auth.jwt() ->> 'role' = 'service_role'
    );
```

### 6. Test Connection

```python
# test_supabase.py
from sqlalchemy import create_engine
import os

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("Connected to Supabase!")
```

## 🔄 Data Migration (If Needed)

If you have existing data to migrate:

### Option 1: Using pg_dump/pg_restore

```bash
# Export from local PostgreSQL
pg_dump -h localhost -U postgres -d lovely --data-only > data.sql

# Import to Supabase
psql postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres < data.sql
```

### Option 2: Using Python Script

```python
# migrate_data.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Old database
old_engine = create_engine("postgresql://user:password@localhost:5432/lovely")
OldSession = sessionmaker(bind=old_engine)

# New Supabase database
new_engine = create_engine(os.getenv("DATABASE_URL"))
NewSession = sessionmaker(bind=new_engine)

# Copy data table by table...
```

## 🎯 Supabase Features to Consider

### 1. Realtime Subscriptions
Monitor WhatsApp messages in real-time:

```sql
-- Enable realtime for messages table
ALTER publication supabase_realtime ADD TABLE messages;
```

### 2. Edge Functions
Replace Celery workers with Supabase Edge Functions for message processing.

### 3. Storage
Store WhatsApp media files in Supabase Storage instead of URLs.

### 4. Auth
Replace your custom auth with Supabase Auth if desired.

## ⚠️ Important Notes

1. **Connection Pooling**: Supabase has connection limits. Use connection pooling:
   ```python
   engine = create_engine(
       DATABASE_URL,
       pool_size=10,
       max_overflow=20,
       pool_pre_ping=True,
       pool_recycle=300
   )
   ```

2. **SSL Required**: Supabase requires SSL connections:
   ```
   DATABASE_URL=postgresql://...?sslmode=require
   ```

3. **Backup**: Always backup your data before migration
4. **Testing**: Test thoroughly in a development environment first

## 🔍 Verification Checklist

- [ ] All tables created successfully
- [ ] Indexes are present
- [ ] Triggers work correctly
- [ ] Can connect from application
- [ ] Can insert/read test data
- [ ] RLS policies don't block legitimate access
- [ ] Performance is acceptable

## 🆘 Troubleshooting

### Connection Refused
- Check if you're using the correct connection string
- Ensure SSL mode is set
- Verify your IP isn't blocked by Supabase

### Permission Denied
- Check RLS policies
- Ensure you're using the correct role
- Verify your connection includes the password

### Slow Queries
- Add appropriate indexes
- Check query plans with EXPLAIN
- Consider upgrading your Supabase plan for better performance 