#!/usr/bin/env python3
"""
Check Messages in Database Script

This script helps verify that messages are being successfully stored in your database.
It shows message counts, recent messages, and can help debug storage issues.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any

# Add paths for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import get_settings
from src.persistence_layer.models import Message, Contact, User, MessageEmbedding

def check_database_connection():
    """Test database connection"""
    settings = get_settings()
    
    print("🔍 Testing Database Connection...")
    print(f"📊 Database URL: {settings.database_url[:50]}...")
    print()
    
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Database connection successful: {row.test}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def get_message_stats():
    """Get overall message statistics"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Total messages
        total_messages = session.query(Message).count()
        
        # Messages by type
        inbound_messages = session.query(Message).filter(Message.is_inbound == True).count()
        outbound_messages = session.query(Message).filter(Message.is_inbound == False).count()
        
        # Messages with text content
        text_messages = session.query(Message).filter(Message.text_content.isnot(None)).count()
        
        # Messages with embeddings
        messages_with_embeddings = session.query(MessageEmbedding).count()
        
        # Recent messages (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_messages = session.query(Message).filter(Message.timestamp >= yesterday).count()
        
        print("📊 Message Statistics:")
        print(f"   Total Messages: {total_messages}")
        print(f"   Inbound Messages: {inbound_messages}")
        print(f"   Outbound Messages: {outbound_messages}")
        print(f"   Text Messages: {text_messages}")
        print(f"   Messages with Embeddings: {messages_with_embeddings}")
        print(f"   Recent Messages (24h): {recent_messages}")
        print()
        
        return {
            'total': total_messages,
            'inbound': inbound_messages,
            'outbound': outbound_messages,
            'text': text_messages,
            'embeddings': messages_with_embeddings,
            'recent': recent_messages
        }
        
    except Exception as e:
        print(f"❌ Error getting message stats: {e}")
        return None
    finally:
        session.close()

def get_recent_messages(limit: int = 10):
    """Get recent messages with details"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get recent messages with contact info
        messages = session.query(Message, Contact).join(Contact).order_by(
            Message.timestamp.desc()
        ).limit(limit).all()
        
        if not messages:
            print("📭 No messages found in database")
            return
        
        print(f"📨 Recent Messages (Last {limit}):")
        print("-" * 80)
        
        for message, contact in messages:
            # Format timestamp
            timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # Format message content
            content = message.text_content or f"[{message.media_type} message]"
            if len(content) > 60:
                content = content[:57] + "..."
            
            # Direction indicator
            direction = "📥" if message.is_inbound else "📤"
            
            print(f"{direction} {timestamp} | {contact.name or contact.whatsapp_id}")
            print(f"   {content}")
            print(f"   ID: {message.id} | WhatsApp ID: {message.whatsapp_message_id}")
            print()
            
    except Exception as e:
        print(f"❌ Error getting recent messages: {e}")
    finally:
        session.close()

def get_messages_by_contact(contact_whatsapp_id: str = None, limit: int = 5):
    """Get messages for a specific contact"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all contacts if no specific contact provided
        if contact_whatsapp_id:
            contact = session.query(Contact).filter(
                Contact.whatsapp_id == contact_whatsapp_id
            ).first()
            
            if not contact:
                print(f"❌ Contact not found: {contact_whatsapp_id}")
                return
                
            contacts = [contact]
        else:
            contacts = session.query(Contact).all()
        
        for contact in contacts:
            print(f"👤 Contact: {contact.name or contact.whatsapp_id}")
            print(f"   WhatsApp ID: {contact.whatsapp_id}")
            print(f"   AI Enabled: {contact.ai_enabled}")
            print(f"   Progression Stage: {contact.progression_stage}")
            print()
            
            # Get messages for this contact
            messages = session.query(Message).filter(
                Message.contact_id == contact.id
            ).order_by(Message.timestamp.desc()).limit(limit).all()
            
            if not messages:
                print("   📭 No messages for this contact")
                print()
                continue
            
            print("   Recent Messages:")
            for message in messages:
                timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                direction = "📥" if message.is_inbound else "📤"
                content = message.text_content or f"[{message.media_type} message]"
                
                print(f"   {direction} {timestamp}: {content}")
            
            print()
            
    except Exception as e:
        print(f"❌ Error getting messages by contact: {e}")
    finally:
        session.close()

def check_embeddings():
    """Check embedding storage status"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get embedding statistics
        total_embeddings = session.query(MessageEmbedding).count()
        
        if total_embeddings == 0:
            print("📭 No message embeddings found")
            return
        
        # Get recent embeddings
        recent_embeddings = session.query(MessageEmbedding).order_by(
            MessageEmbedding.created_at.desc()
        ).limit(5).all()
        
        print(f"🧠 Embedding Statistics:")
        print(f"   Total Embeddings: {total_embeddings}")
        print()
        
        print("Recent Embeddings:")
        for embedding in recent_embeddings:
            print(f"   Message ID: {embedding.message_id}")
            print(f"   Model: {embedding.embedding_model}")
            print(f"   Dimension: {embedding.embedding_dimension}")
            print(f"   Created: {embedding.created_at}")
            print()
            
    except Exception as e:
        print(f"❌ Error checking embeddings: {e}")
    finally:
        session.close()

def main():
    """Main function"""
    print("Database Message Checker")
    print("=" * 40)
    print()
    
    # Check connection
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    print()
    
    # Get message statistics
    stats = get_message_stats()
    if not stats:
        print("❌ Cannot get message statistics")
        sys.exit(1)
    
    print()
    
    # Show recent messages
    get_recent_messages(limit=5)
    
    print()
    
    # Show messages by contact
    get_messages_by_contact(limit=3)
    
    print()
    
    # Check embeddings
    check_embeddings()
    
    print("✅ Message check completed!")

if __name__ == "__main__":
    main() 