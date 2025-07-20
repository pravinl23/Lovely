-- Supabase Schema for WhatsApp AI Assistant
-- Drop existing tables if they exist (careful in production!)
DROP TABLE IF EXISTS message_embeddings CASCADE;
DROP TABLE IF EXISTS outbound_replies CASCADE;
DROP TABLE IF EXISTS facts CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS contacts CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop existing enum type if it exists
DROP TYPE IF EXISTS progression_stage CASCADE;

-- Create custom enum type for progression stages
CREATE TYPE progression_stage AS ENUM (
    'discovery',
    'rapport',
    'logistics_candidate',
    'proposal',
    'negotiation',
    'confirmation',
    'post_confirmation'
);

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    whatsapp_phone_number_id VARCHAR(255) UNIQUE,
    whatsapp_api_token TEXT, -- Encrypted
    global_automation_enabled BOOLEAN DEFAULT FALSE,
    persona_profile_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Contacts table
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    whatsapp_id VARCHAR(255) NOT NULL, -- Phone number
    name VARCHAR(255),
    ai_enabled BOOLEAN DEFAULT FALSE,
    progression_stage progression_stage DEFAULT 'discovery',
    
    -- Metrics
    last_inbound_message_at TIMESTAMP WITH TIME ZONE,
    last_ai_reply_at TIMESTAMP WITH TIME ZONE,
    response_latency_avg FLOAT,
    reciprocity_ratio FLOAT,
    computed_metrics_json JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint
    CONSTRAINT unique_user_contact UNIQUE (user_id, whatsapp_id)
);

-- Messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    whatsapp_message_id VARCHAR(255) UNIQUE NOT NULL, -- wamid
    
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    is_inbound BOOLEAN NOT NULL,
    text_content TEXT,
    media_type VARCHAR(50),
    media_url TEXT,
    
    -- Extracted data
    extracted_intents_json JSONB,
    extracted_entities_json JSONB,
    sentiment VARCHAR(50),
    raw_webhook_payload_json JSONB, -- Redacted version
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Facts table
CREATE TABLE facts (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    origin_message_id INTEGER REFERENCES messages(id),
    
    extraction_confidence FLOAT DEFAULT 1.0,
    first_observed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_reinforced TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decay_weight FLOAT DEFAULT 1.0,
    version INTEGER DEFAULT 1,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Outbound replies table
CREATE TABLE outbound_replies (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages(id), -- Reply to this message
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    generated_text TEXT NOT NULL,
    full_prompt_context_json JSONB,
    llm_meta_tags_json JSONB,
    
    status VARCHAR(50) NOT NULL, -- sent, failed
    failure_reason TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);



-- Message embeddings table
CREATE TABLE message_embeddings (
    id SERIAL PRIMARY KEY,
    message_id INTEGER UNIQUE NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    embedding_model VARCHAR(100) NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    embedding_vector JSONB NOT NULL, -- In production, use vector type with pgvector
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_contact_user_whatsapp ON contacts(user_id, whatsapp_id);
CREATE INDEX idx_message_contact_timestamp ON messages(contact_id, timestamp);
CREATE INDEX idx_message_whatsapp_id ON messages(whatsapp_message_id);
CREATE INDEX idx_fact_contact_key ON facts(contact_id, key);
CREATE INDEX idx_fact_last_reinforced ON facts(last_reinforced);
CREATE INDEX idx_embedding_message ON message_embeddings(message_id);

-- Create update trigger for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facts_updated_at BEFORE UPDATE ON facts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) - Enable after migration
-- Supabase uses RLS for security. Here's a basic setup:

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbound_replies ENABLE ROW LEVEL SECURITY;

ALTER TABLE message_embeddings ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (adjust based on your auth needs)
-- These assume you're using Supabase Auth with JWT

-- Users can only see their own data
CREATE POLICY "Users can view own data" ON users
    FOR ALL USING (auth.uid()::text = id::text);

-- Users can only see their own contacts
CREATE POLICY "Users can view own contacts" ON contacts
    FOR ALL USING (user_id IN (
        SELECT id FROM users WHERE auth.uid()::text = id::text
    ));

-- Users can only see messages for their contacts
CREATE POLICY "Users can view own messages" ON messages
    FOR ALL USING (user_id IN (
        SELECT id FROM users WHERE auth.uid()::text = id::text
    ));

-- Apply similar policies to other tables...

-- Create a default user (REMOVE IN PRODUCTION)
INSERT INTO users (email, hashed_password, whatsapp_phone_number_id, global_automation_enabled)
VALUES ('default@example.com', 'placeholder_hash', '[YOUR-WHATSAPP-PHONE-NUMBER-ID]', true); 