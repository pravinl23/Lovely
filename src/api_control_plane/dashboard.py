"""
Dashboard API endpoints for managing contacts and viewing conversations
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import select, desc, func
from pydantic import BaseModel

from src.persistence_layer.db_manager import DatabaseManager
from src.persistence_layer.models import Contact, Message, User
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Pydantic models for API responses
class ContactResponse(BaseModel):
    id: int
    whatsapp_id: str
    name: str | None
    ai_enabled: bool
    progression_stage: str
    last_inbound_message_at: datetime | None
    message_count: int
    
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    text_content: str | None
    is_inbound: bool
    timestamp: datetime
    sentiment: str | None
    
    class Config:
        from_attributes = True

class ConversationSummary(BaseModel):
    contact_info: ContactResponse
    message_count: int
    recent_messages: List[MessageResponse]
    conversation_summary: str


@router.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Serve the dashboard HTML page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>WhatsApp AI Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #25D366; text-align: center; margin-bottom: 30px; }
            .contacts-grid { display: grid; gap: 15px; margin-bottom: 30px; }
            .contact-card { 
                background: #f9f9f9; 
                padding: 15px; 
                border-radius: 8px; 
                border: 1px solid #ddd;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .contact-card:hover { background: #e8f5e8; transform: translateY(-2px); }
            .contact-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
            .contact-name { font-weight: bold; font-size: 16px; }
            .contact-phone { color: #666; font-size: 14px; }
            .ai-toggle { 
                background: #ddd; 
                border: none; 
                padding: 5px 15px; 
                border-radius: 20px; 
                cursor: pointer;
                transition: background 0.3s;
            }
            .ai-toggle.enabled { background: #25D366; color: white; }
            .contact-stats { display: flex; gap: 15px; font-size: 12px; color: #666; }
            .conversation-view { 
                display: none; 
                background: white; 
                padding: 20px; 
                border-radius: 8px; 
                margin-top: 20px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .message { 
                padding: 8px 12px; 
                margin: 5px 0; 
                border-radius: 12px; 
                max-width: 70%;
            }
            .message.inbound { 
                background: #e3f2fd; 
                margin-left: 0; 
                margin-right: auto;
            }
            .message.outbound { 
                background: #25D366; 
                color: white; 
                margin-left: auto; 
                margin-right: 0;
            }
            .back-btn { 
                background: #25D366; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 5px; 
                cursor: pointer;
                margin-bottom: 15px;
            }
            .loading { text-align: center; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 WhatsApp AI Dashboard</h1>
            
            <div id="contacts-list">
                <div class="loading">Loading contacts...</div>
            </div>
            
            <div id="conversation-view" class="conversation-view">
                <button class="back-btn" onclick="showContactsList()">← Back to Contacts</button>
                <div id="conversation-content"></div>
            </div>
        </div>

        <script>
            let contacts = [];
            
            async function loadContacts() {
                try {
                    const response = await fetch('/dashboard/contacts');
                    contacts = await response.json();
                    renderContacts();
                } catch (error) {
                    document.getElementById('contacts-list').innerHTML = '<div class="loading">Error loading contacts</div>';
                }
            }
            
            function renderContacts() {
                const html = contacts.map(contact => `
                    <div class="contact-card" onclick="showConversation(${contact.id})">
                        <div class="contact-header">
                            <div>
                                <div class="contact-name">${contact.name || 'Unknown'}</div>
                                <div class="contact-phone">${contact.whatsapp_id}</div>
                            </div>
                            <button class="ai-toggle ${contact.ai_enabled ? 'enabled' : ''}" 
                                    onclick="event.stopPropagation(); toggleAI(${contact.id}, ${!contact.ai_enabled})">
                                ${contact.ai_enabled ? 'AI ON' : 'AI OFF'}
                            </button>
                        </div>
                        <div class="contact-stats">
                            <span>📊 Stage: ${contact.progression_stage}</span>
                            <span>💬 Messages: ${contact.message_count}</span>
                            <span>⏰ Last: ${contact.last_inbound_message_at ? new Date(contact.last_inbound_message_at).toLocaleDateString() : 'Never'}</span>
                        </div>
                    </div>
                `).join('');
                
                document.getElementById('contacts-list').innerHTML = html;
            }
            
            async function toggleAI(contactId, enabled) {
                try {
                    await fetch(`/dashboard/contacts/${contactId}/ai`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ enabled })
                    });
                    
                    // Update local state
                    const contact = contacts.find(c => c.id === contactId);
                    if (contact) contact.ai_enabled = enabled;
                    renderContacts();
                } catch (error) {
                    alert('Failed to update AI status');
                }
            }
            
            async function showConversation(contactId) {
                document.getElementById('contacts-list').style.display = 'none';
                document.getElementById('conversation-view').style.display = 'block';
                document.getElementById('conversation-content').innerHTML = '<div class="loading">Loading conversation...</div>';
                
                try {
                    const response = await fetch(`/dashboard/contacts/${contactId}/conversation`);
                    const data = await response.json();
                    
                    const messagesHtml = data.recent_messages.map(msg => `
                        <div class="message ${msg.is_inbound ? 'inbound' : 'outbound'}">
                            ${msg.text_content || '[Media message]'}
                            <div style="font-size: 10px; opacity: 0.7; margin-top: 3px;">
                                ${new Date(msg.timestamp).toLocaleString()}
                            </div>
                        </div>
                    `).join('');
                    
                    document.getElementById('conversation-content').innerHTML = `
                        <h2>${data.contact_info.name || data.contact_info.whatsapp_id}</h2>
                        <div style="background: #f0f0f0; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                            <strong>Summary:</strong> ${data.conversation_summary}
                        </div>
                        <h3>Recent Messages (${data.message_count} total)</h3>
                        <div style="height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 8px;">
                            ${messagesHtml}
                        </div>
                    `;
                } catch (error) {
                    document.getElementById('conversation-content').innerHTML = '<div class="loading">Error loading conversation</div>';
                }
            }
            
            function showContactsList() {
                document.getElementById('contacts-list').style.display = 'block';
                document.getElementById('conversation-view').style.display = 'none';
            }
            
            // Load contacts on page load
            loadContacts();
        </script>
    </body>
    </html>
    """
    return html_content


@router.get("/contacts", response_model=List[ContactResponse])
async def get_contacts():
    """Get all contacts with message counts"""
    db_manager = DatabaseManager()
    
    async with db_manager.async_session() as session:
        # Query contacts with message counts
        query = select(
            Contact,
            func.count(Message.id).label('message_count')
        ).outerjoin(
            Message, Contact.id == Message.contact_id
        ).group_by(Contact.id).order_by(desc(Contact.last_inbound_message_at))
        
        result = await session.execute(query)
        
        contacts_data = []
        for contact, message_count in result:
            contacts_data.append(ContactResponse(
                id=contact.id,
                whatsapp_id=contact.whatsapp_id,
                name=contact.name,
                ai_enabled=contact.ai_enabled,
                progression_stage=contact.progression_stage.value,
                last_inbound_message_at=contact.last_inbound_message_at,
                message_count=message_count or 0
            ))
        
        return contacts_data


@router.post("/contacts/{contact_id}/ai")
async def toggle_contact_ai(contact_id: int, request: Dict[str, bool]):
    """Enable/disable AI for a specific contact"""
    db_manager = DatabaseManager()
    
    async with db_manager.async_session() as session:
        result = await session.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact.ai_enabled = request["enabled"]
        await session.commit()
        
        logger.info(f"AI {'enabled' if request['enabled'] else 'disabled'} for contact {contact_id}")
        
        return {"success": True, "ai_enabled": contact.ai_enabled}


@router.get("/contacts/{contact_id}/conversation", response_model=ConversationSummary)
async def get_conversation(contact_id: int):
    """Get conversation history and summary for a contact"""
    db_manager = DatabaseManager()
    
    async with db_manager.async_session() as session:
        # Get contact
        contact_result = await session.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = contact_result.scalar_one_or_none()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Get message count
        count_result = await session.execute(
            select(func.count(Message.id)).where(Message.contact_id == contact_id)
        )
        message_count = count_result.scalar()
        
        # Get recent messages (last 20)
        messages_result = await session.execute(
            select(Message)
            .where(Message.contact_id == contact_id)
            .order_by(desc(Message.timestamp))
            .limit(20)
        )
        messages = list(reversed(messages_result.scalars().all()))
        
        # Create simple conversation summary
        inbound_count = sum(1 for msg in messages if msg.is_inbound)
        outbound_count = len(messages) - inbound_count
        
        summary = f"This conversation has {message_count} total messages ({inbound_count} received, {outbound_count} sent). "
        
        if messages:
            last_message = messages[-1]
            summary += f"Last activity: {last_message.timestamp.strftime('%Y-%m-%d %H:%M')}. "
            
            # Analyze sentiment
            sentiments = [msg.sentiment for msg in messages if msg.sentiment and msg.is_inbound]
            if sentiments:
                positive_count = sum(1 for s in sentiments if s in ['positive', 'excited', 'warm'])
                if positive_count > len(sentiments) / 2:
                    summary += "Overall tone appears positive and engaged."
                else:
                    summary += "Mixed conversational tone."
            else:
                summary += "Conversation is developing."
        else:
            summary += "No messages yet."
        
        return ConversationSummary(
            contact_info=ContactResponse(
                id=contact.id,
                whatsapp_id=contact.whatsapp_id,
                name=contact.name,
                ai_enabled=contact.ai_enabled,
                progression_stage=contact.progression_stage.value,
                last_inbound_message_at=contact.last_inbound_message_at,
                message_count=message_count
            ),
            message_count=message_count,
            recent_messages=[
                MessageResponse(
                    id=msg.id,
                    text_content=msg.text_content,
                    is_inbound=msg.is_inbound,
                    timestamp=msg.timestamp,
                    sentiment=msg.sentiment
                ) for msg in messages
            ],
            conversation_summary=summary
        ) 