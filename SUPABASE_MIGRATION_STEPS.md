# Supabase Migration Steps for WhatsApp Automation

## 🎯 Your Supabase Project Details

- **Project URL**: https://gpqwxdexrblnfwlkhosv.supabase.co
- **Anonymous Key**: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwcXd4ZGV4cmJsbmZ3bGtob3N2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI5NTUwOTAsImV4cCI6MjA2ODUzMTA5MH0.QKUmkXcdOm3IyBtYanFZm4Z2pboHojwySOrpatNOffs

## 📋 Prerequisites

1. **Get your Supabase Database Password**:
   - Go to https://supabase.com/dashboard/project/gpqwxdexrblnfwlkhosv
   - Navigate to **Settings** → **Database**
   - Copy the **Database Password**

2. **Ensure your local PostgreSQL is running** (if you have existing data to migrate)

## 🚀 Migration Process

### Step 1: Setup Environment

```bash
# Run the setup script
./scripts/setup_supabase.sh
```

This will:
- Create/activate virtual environment
- Install dependencies
- Prompt for your Supabase database password

### Step 2: Run Migration

```bash
# Set your Supabase database password
export SUPABASE_DB_PASSWORD="your_database_password_here"

# Run the migration script
python scripts/migrate_to_supabase.py
```

The migration script will:
1. ✅ Test connection to Supabase
2. ✅ Execute schema migration (creates all tables)
3. ✅ Enable pgvector extension for embeddings
4. ✅ Configure RLS policies for service access
5. ✅ Migrate existing data (if you choose to)
6. ✅ Update your `.env` file with Supabase configuration

### Step 3: Test Connection

```bash
python scripts/test_supabase_connection.py
```

This will verify:
- Database connection
- Table existence
- pgvector extension
- Basic CRUD operations

### Step 4: Update Your Application

Your application should work with minimal changes since Supabase is PostgreSQL-compatible. The main changes are:

1. **Database URL**: Updated in `.env` file
2. **SSL Mode**: Automatically configured for Supabase
3. **Connection Pooling**: Recommended for production

## 🔧 Manual Steps (if needed)

### If you prefer manual migration:

1. **Execute Schema in Supabase Dashboard**:
   - Go to https://supabase.com/dashboard/project/gpqwxdexrblnfwlkhosv/sql
   - Copy contents of `supabase_schema.sql`
   - Paste and execute

2. **Enable pgvector**:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Update your `.env` file**:
   ```bash
   # Old
   DATABASE_URL=postgresql://pravinlohani@localhost:5432/whatsapp_automation
   
   # New
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.gpqwxdexrblnfwlkhosv.supabase.co:5432/postgres?sslmode=require
   
   # Add Supabase config
   SUPABASE_URL=https://gpqwxdexrblnfwlkhosv.supabase.co
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwcXd4ZGV4cmJsbmZ3bGtob3N2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI5NTUwOTAsImV4cCI6MjA2ODUzMTA5MH0.QKUmkXcdOm3IyBtYanFZm4Z2pboHojwySOrpatNOffs
   ```

## 🎯 What Gets Migrated

### Schema (Tables):
- ✅ `users` - User accounts and WhatsApp configuration
- ✅ `contacts` - WhatsApp contacts with AI settings
- ✅ `messages` - All WhatsApp messages
- ✅ `facts` - Extracted facts about contacts
- ✅ `outbound_replies` - AI-generated replies
- ✅ `briefings` - Contact briefings
- ✅ `message_embeddings` - Vector embeddings for semantic search

### Features:
- ✅ Row Level Security (RLS) configured for service access
- ✅ pgvector extension for embeddings
- ✅ All indexes and triggers
- ✅ Custom enum types (progression_stage)

## 🔍 Verification Checklist

After migration, verify:

- [ ] Can connect to Supabase database
- [ ] All tables exist and are accessible
- [ ] pgvector extension is enabled
- [ ] Can perform basic CRUD operations
- [ ] Your application starts without errors
- [ ] WhatsApp webhooks still work
- [ ] AI features (embeddings, LLM) work correctly

## 🚨 Troubleshooting

### Connection Issues:
```bash
# Test connection manually
psql postgresql://postgres:YOUR_PASSWORD@db.gpqwxdexrblnfwlkhosv.supabase.co:5432/postgres?sslmode=require
```

### Permission Issues:
- Check RLS policies in Supabase dashboard
- Ensure you're using the correct database password

### Performance Issues:
- Monitor connection pool usage
- Consider upgrading Supabase plan if needed

## 🎉 Post-Migration Benefits

1. **Scalability**: Supabase handles scaling automatically
2. **Backups**: Automatic daily backups
3. **Monitoring**: Built-in performance monitoring
4. **Security**: Enterprise-grade security
5. **Real-time**: Can enable real-time subscriptions
6. **Edge Functions**: Can replace Celery workers

## 📞 Support

If you encounter issues:
1. Check the Supabase dashboard logs
2. Review the migration script output
3. Test connection with the provided test script
4. Check your `.env` file configuration 