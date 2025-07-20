-- Contact Manager Database Setup
-- Run this in your Supabase SQL editor

-- Create contacts table
CREATE TABLE IF NOT EXISTS contacts (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  phone_number TEXT UNIQUE NOT NULL,
  is_whitelisted BOOLEAN DEFAULT FALSE,
  knowledge_file TEXT DEFAULT 'default.json',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Create app_settings table
CREATE TABLE IF NOT EXISTS app_settings (
  id INTEGER PRIMARY KEY DEFAULT 1,
  starred_contact_id INTEGER REFERENCES contacts(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert demo contacts
INSERT INTO contacts (name, phone_number, knowledge_file) VALUES
  ('Bob', '647', 'bob.json'),
  ('Isabella', '416', 'isabella.json'),
  ('Adam', '289', 'adam.json')
ON CONFLICT (phone_number) DO NOTHING;

-- Insert default app settings
INSERT INTO app_settings (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_contacts_phone_number ON contacts(phone_number);
CREATE INDEX IF NOT EXISTS idx_contacts_whitelisted ON contacts(is_whitelisted);

-- Enable Row Level Security (RLS) - optional for demo
-- ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

-- Create policies for RLS (if enabled)
-- CREATE POLICY "Allow all operations on contacts" ON contacts FOR ALL USING (true);
-- CREATE POLICY "Allow all operations on app_settings" ON app_settings FOR ALL USING (true); 