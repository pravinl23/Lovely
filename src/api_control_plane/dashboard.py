"""
Dashboard API endpoints for monitoring and managing conversations
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

from src.persistence_layer.supabase_manager import SupabaseManager
from src.persistence_layer.models import Contact, Message
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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
    """Dashboard home page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhatsApp Automation Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
            .contact-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; cursor: pointer; }
            .contact-item:hover { background: #f8f9fa; }
            .contact-header { display: flex; justify-content: space-between; align-items: center; }
            .ai-toggle { padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; }
            .ai-on { background: #28a745; color: white; }
            .ai-off { background: #dc3545; color: white; }
            .contact-stats { font-size: 0.9em; color: #666; }
            .contact-stats span { margin-right: 15px; }
            .loading { text-align: center; padding: 20px; color: #666; }
            #conversation-view { display: none; }
            .message { margin: 10px 0; padding: 10px; border-radius: 8px; }
            .inbound { background: #e3f2fd; margin-right: 20%; }
            .outbound { background: #f3e5f5; margin-left: 20%; text-align: right; }
            .back-btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>WhatsApp Automation Dashboard</h1>
                <p>Monitor and manage your automated conversations</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="total-contacts">-</div>
                    <div>Total Contacts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="ai-enabled">-</div>
                    <div>AI Enabled</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-messages">-</div>
                    <div>Total Messages</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="active-conversations">-</div>
                    <div>Active Today</div>
                </div>
            </div>
            
            <div id="contacts-list">
                <h2>Contacts</h2>
                <div id="contacts-container"></div>
            </div>
            
            <div id="conversation-view">
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
                    
                    // Update stats
                    document.getElementById('total-contacts').textContent = contacts.length;
                    document.getElementById('ai-enabled').textContent = contacts.filter(c => c.ai_enabled).length;
                    document.getElementById('total-messages').textContent = contacts.reduce((sum, c) => sum + c.message_count, 0);
                    document.getElementById('active-conversations').textContent = contacts.filter(c => {
                        if (!c.last_inbound_message_at) return false;
                        const lastMessage = new Date(c.last_inbound_message_at);
                        const today = new Date();
                        return lastMessage.toDateString() === today.toDateString();
                    }).length;
                    
                    renderContacts();
                } catch (error) {
                    console.error('Failed to load contacts:', error);
                }
            }
            
            function renderContacts() {
                const html = contacts.map(contact => `
                    <div class="contact-item" onclick="showConversation(${contact.id})">
                        <div class="contact-header">
                            <div>
                                <strong>${contact.name || contact.whatsapp_id}</strong>
                                <button class="ai-toggle ${contact.ai_enabled ? 'ai-on' : 'ai-off'}" 
                                    onclick="event.stopPropagation(); toggleAI(${contact.id}, ${!contact.ai_enabled})">
                                    ${contact.ai_enabled ? 'AI ON' : 'AI OFF'}
                                </button>
                            </div>
                        </div>
                        <div class="contact-stats">
                            <span> Stage: ${contact.progression_stage}</span>
                            <span> Messages: ${contact.message_count}</span>
                            <span>⏰ Last: ${contact.last_inbound_message_at ? new Date(contact.last_inbound_message_at).toLocaleDateString() : 'Never'}</span>
                        </div>
                    </div>
                `).join('');
                
                document.getElementById('contacts-container').innerHTML = html;
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
    db_manager = SupabaseManager()
    
    async with db_manager as db:
        try:
            # Get all contacts
            contacts_result = db.supabase.table('contacts').select('*').order('last_inbound_message_at', desc=True).execute()
            contacts = contacts_result.data if contacts_result.data else []
            
            contacts_data = []
            for contact in contacts:
                # Get message count for this contact
                messages_result = db.supabase.table('messages').select('id').eq('contact_id', contact['id']).execute()
                message_count = len(messages_result.data) if messages_result.data else 0
                
                contacts_data.append(ContactResponse(
                    id=contact['id'],
                    whatsapp_id=contact['whatsapp_id'],
                    name=contact.get('name'),
                    ai_enabled=contact.get('ai_enabled', False),
                    progression_stage=contact.get('progression_stage', 'discovery'),
                    last_inbound_message_at=datetime.fromisoformat(contact['last_inbound_message_at']) if contact.get('last_inbound_message_at') else None,
                    message_count=message_count
                ))
            
            return contacts_data
            
        except Exception as e:
            logger.error(f"Error getting contacts: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to load contacts")


@router.post("/contacts/{contact_id}/ai")
async def toggle_contact_ai(contact_id: int, request: Dict[str, bool]):
    """Enable/disable AI for a specific contact"""
    db_manager = SupabaseManager()
    
    async with db_manager as db:
        try:
            # Get contact
            contact_result = db.supabase.table('contacts').select('*').eq('id', contact_id).execute()
            contact = contact_result.data[0] if contact_result.data else None
            
            if not contact:
                raise HTTPException(status_code=404, detail="Contact not found")
            
            # Update AI status
            db.supabase.table('contacts').update({
                'ai_enabled': request["enabled"],
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', contact_id).execute()
            
            logger.info(f"AI {'enabled' if request['enabled'] else 'disabled'} for contact {contact_id}")
            
            return {"success": True, "ai_enabled": request["enabled"]}
            
        except Exception as e:
            logger.error(f"Error toggling AI for contact {contact_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to update AI status")


@router.get("/contacts/{contact_id}/conversation", response_model=ConversationSummary)
async def get_conversation(contact_id: int):
    """Get conversation history and summary for a contact"""
    db_manager = SupabaseManager()
    
    async with db_manager as db:
        try:
            # Get contact
            contact_result = db.supabase.table('contacts').select('*').eq('id', contact_id).execute()
            contact = contact_result.data[0] if contact_result.data else None
                
            if not contact:
                raise HTTPException(status_code=404, detail="Contact not found")
            
            # Get message count
            messages_result = db.supabase.table('messages').select('*').eq('contact_id', contact_id).execute()
            messages = messages_result.data if messages_result.data else []
            message_count = len(messages)
            
            # Get recent messages (last 20)
            recent_messages = sorted(messages, key=lambda x: x['timestamp'], reverse=True)[:20]
            recent_messages.reverse()  # Put back in chronological order
            
            # Create simple conversation summary
            inbound_count = sum(1 for msg in messages if msg.get('is_inbound'))
            outbound_count = len(messages) - inbound_count
            
            summary = f"This conversation has {message_count} total messages ({inbound_count} received, {outbound_count} sent). "
            
            if recent_messages:
                last_message = recent_messages[-1]
                last_timestamp = datetime.fromisoformat(last_message['timestamp'])
                summary += f"Last activity: {last_timestamp.strftime('%Y-%m-%d %H:%M')}. "
                
                # Analyze sentiment
                sentiments = [msg.get('sentiment') for msg in messages if msg.get('sentiment') and msg.get('is_inbound')]
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
                    id=contact['id'],
                    whatsapp_id=contact['whatsapp_id'],
                    name=contact.get('name'),
                    ai_enabled=contact.get('ai_enabled', False),
                    progression_stage=contact.get('progression_stage', 'discovery'),
                    last_inbound_message_at=datetime.fromisoformat(contact['last_inbound_message_at']) if contact.get('last_inbound_message_at') else None,
                    message_count=message_count
                ),
                message_count=message_count,
                recent_messages=[
                    MessageResponse(
                        id=msg['id'],
                        text_content=msg.get('text_content'),
                        is_inbound=msg.get('is_inbound', False),
                        timestamp=datetime.fromisoformat(msg['timestamp']),
                        sentiment=msg.get('sentiment')
                    ) for msg in recent_messages
                ],
                conversation_summary=summary
            )
            
        except Exception as e:
            logger.error(f"Error getting conversation for contact {contact_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to load conversation") 