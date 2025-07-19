#!/bin/bash

# Supabase Migration Setup Script
# This script helps set up the environment for migrating to Supabase

set -e  # Exit on any error

echo "🚀 Supabase Migration Setup"
echo "=========================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one with your configuration."
    echo "   You can copy from .env.example if it exists."
    exit 1
fi

# Check for Supabase password
if [ -z "$SUPABASE_DB_PASSWORD" ]; then
    echo "⚠️  SUPABASE_DB_PASSWORD environment variable not set."
    echo "   Please set it with your Supabase database password:"
    echo "   export SUPABASE_DB_PASSWORD='your_password_here'"
    echo ""
    echo "   You can get this from: Supabase Dashboard > Settings > Database"
    echo ""
    read -p "Enter your Supabase database password: " supabase_password
    export SUPABASE_DB_PASSWORD="$supabase_password"
fi

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Run the migration script:"
echo "      python scripts/migrate_to_supabase.py"
echo ""
echo "   2. Test the connection:"
echo "      python scripts/test_supabase_connection.py"
echo ""
echo "   3. Start your application:"
echo "      python src/main.py" 