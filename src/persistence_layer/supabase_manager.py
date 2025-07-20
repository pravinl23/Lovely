"""
Supabase-based database manager for handling all persistence operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
from cryptography.fernet import Fernet
import numpy as np

from config.settings import settings
from supabase import create_client, Client
from src.perception_layer.models import Message as PerceptionMessage
from src.utils.logging import get_logger
from src.utils.embeddings import EmbeddingGenerator

logger = get_logger(__name__)


class SupabaseManager:
    """Manages all database operations using Supabase client"""
    
    def __init__(self):
        # Initialize Supabase client with service role key for admin operations
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key.get_secret_value()
        )
        
        # Initialize encryption
        self.fernet = Fernet(settings.encryption_key.get_secret_value().encode())
        
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    # User operations
    async def create_user(
        self, 
        email: str, 
        hashed_password: str,
        whatsapp_phone_number_id: str,
        whatsapp_api_token: str
    ) -> Dict[str, Any]:
        """Create a new user"""
        try:
            user_data = {
                'email': email,
                'hashed_password': hashed_password,
                'whatsapp_phone_number_id': whatsapp_phone_number_id,
                'whatsapp_api_token': self.encrypt_data(whatsapp_api_token),
                'global_automation_enabled': False,
                'persona_profile_json': {}
            }
            
            result = self.supabase.table('users').insert(user_data).execute()
            logger.info(f"Created user: {email}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            result = self.supabase.table('users').select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    async def get_user_by_phone_id(self, phone_number_id: str) -> Optional[Dict[str, Any]]:
        """Get user by WhatsApp phone number ID"""
        try:
            result = self.supabase.table('users').select('*').eq('whatsapp_phone_number_id', phone_number_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by phone ID: {str(e)}")
            return None
    
    async def get_user_outbound_messages(
        self,
        user_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user's outbound messages"""
        try:
            result = self.supabase.table('messages').select('*').eq('user_id', user_id).eq('is_inbound', False).order('timestamp', desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting user outbound messages: {str(e)}")
            return []
    
    async def get_recent_outbound_messages(
        self,
        contact_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent outbound messages for a contact"""
        try:
            result = self.supabase.table('messages').select('*').eq('contact_id', contact_id).eq('is_inbound', False).order('timestamp', desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting recent outbound messages: {str(e)}")
            return []
    
    # Contact operations
    async def get_or_create_contact(
        self,
        user_id: int,
        whatsapp_id: str,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get existing contact or create new one"""
        try:
            # Try to get existing contact
            result = self.supabase.table('contacts').select('*').eq('user_id', user_id).eq('whatsapp_id', whatsapp_id).execute()
            
            if result.data:
                return result.data[0]
            
            # Create new contact
            contact_data = {
                'user_id': user_id,
                'whatsapp_id': whatsapp_id,
                'name': name,
                'ai_enabled': False,
                'progression_stage': 'discovery',
                'computed_metrics_json': {}
            }
            
            result = self.supabase.table('contacts').insert(contact_data).execute()
            logger.info(f"Created contact: {whatsapp_id}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting/creating contact: {str(e)}")
            raise
    
    async def update_contact_metrics(
        self,
        contact_id: int,
        last_inbound_message_at: Optional[datetime] = None,
        last_ai_reply_at: Optional[datetime] = None
    ):
        """Update contact metrics"""
        try:
            update_data = {}
            if last_inbound_message_at:
                update_data['last_inbound_message_at'] = last_inbound_message_at.isoformat()
            if last_ai_reply_at:
                update_data['last_ai_reply_at'] = last_ai_reply_at.isoformat()
            
            if update_data:
                self.supabase.table('contacts').update(update_data).eq('id', contact_id).execute()
                logger.info(f"Updated contact metrics: {contact_id}")
                
        except Exception as e:
            logger.error(f"Error updating contact metrics: {str(e)}")
    
    async def update_contact_progression_stage(
        self,
        contact_id: int,
        new_stage: str
    ):
        """Update contact progression stage"""
        try:
            self.supabase.table('contacts').update({
                'progression_stage': new_stage,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', contact_id).execute()
            logger.info(f"Updated contact {contact_id} progression stage to: {new_stage}")
        except Exception as e:
            logger.error(f"Error updating contact progression stage: {str(e)}")
    
    async def calculate_contact_metrics(self, contact_id: int):
        """Calculate and update contact metrics based on recent messages"""
        try:
            # Get recent messages for this contact
            messages = await self.get_recent_messages(contact_id, limit=100)
            
            if not messages:
                return
            
            # Calculate response latency
            response_times = []
            for i in range(len(messages) - 1):
                if messages[i]['is_inbound'] and not messages[i+1]['is_inbound']:
                    current_time = datetime.fromisoformat(messages[i]['timestamp'])
                    next_time = datetime.fromisoformat(messages[i+1]['timestamp'])
                    delta = next_time - current_time
                    response_times.append(delta.total_seconds())
            
            # Calculate reciprocity ratio
            inbound_count = sum(1 for m in messages if m['is_inbound'])
            outbound_count = len(messages) - inbound_count
            
            # Update metrics
            update_data = {}
            if response_times:
                update_data['response_latency_avg'] = sum(response_times) / len(response_times)
            
            if outbound_count > 0:
                update_data['reciprocity_ratio'] = inbound_count / outbound_count
            
            if update_data:
                self.supabase.table('contacts').update(update_data).eq('id', contact_id).execute()
                logger.info(f"Calculated metrics for contact: {contact_id}")
                
        except Exception as e:
            logger.error(f"Error calculating contact metrics: {str(e)}")
    
    # Message operations
    async def store_message(self, perception_message: PerceptionMessage) -> Dict[str, Any]:
        """Store a message in the database"""
        try:
            # Get or create contact first
            contact = await self.get_or_create_contact(
                user_id=1,  # Default user ID for now
                whatsapp_id=perception_message.sender_id,
                name=None  # We don't have sender_name in this model
            )
            
            # Prepare message data
            message_data = {
                'contact_id': contact['id'],
                'user_id': 1,  # Default user ID
                'whatsapp_message_id': perception_message.message_id,
                'timestamp': perception_message.timestamp.isoformat(),
                'is_inbound': perception_message.is_inbound,
                'text_content': perception_message.text_content,
                'media_type': perception_message.media_type,
                'media_url': perception_message.media_url,
                'extracted_intents_json': perception_message.annotations.to_dict()['intents'] if perception_message.annotations else None,
                'extracted_entities_json': perception_message.annotations.to_dict()['entities'] if perception_message.annotations else None,
                'sentiment': perception_message.annotations.sentiment.value if perception_message.annotations and perception_message.annotations.sentiment else None,
                'raw_webhook_payload_json': self._redact_webhook_payload(perception_message.raw_webhook_payload)
            }
            
            # Store message
            result = self.supabase.table('messages').insert(message_data).execute()
            stored_message = result.data[0] if result.data else None
            
            if stored_message:
                logger.info(f"Stored message: {perception_message.message_id}")
                
                # Update contact metrics
                if perception_message.is_inbound:
                    await self.update_contact_metrics(
                        contact_id=contact['id'],
                        last_inbound_message_at=perception_message.timestamp
                    )
                
                # Generate and store embedding if text content exists
                if perception_message.text_content:
                    await self.store_message_embedding(
                        message_id=stored_message['id'],
                        text=perception_message.text_content
                    )
            
            return stored_message
            
        except Exception as e:
            logger.error(f"Error storing message: {str(e)}")
            raise
    
    def _redact_webhook_payload(self, payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Redact sensitive information from webhook payload"""
        if not payload:
            return None
        
        def redact_dict(d: dict):
            sensitive_keys = {'access_token', 'token', 'password', 'secret', 'key'}
            redacted = {}
            for k, v in d.items():
                if k.lower() in sensitive_keys:
                    redacted[k] = '[REDACTED]'
                elif isinstance(v, dict):
                    redacted[k] = redact_dict(v)
                elif isinstance(v, list):
                    redacted[k] = [redact_dict(item) if isinstance(item, dict) else item for item in v]
                else:
                    redacted[k] = v
            return redacted
        
        return redact_dict(payload)
    
    async def get_recent_messages(
        self,
        contact_id: int,
        limit: int = 20,
        before_timestamp: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get recent messages for a contact"""
        try:
            query = self.supabase.table('messages').select('*').eq('contact_id', contact_id).order('timestamp', desc=True).limit(limit)
            
            if before_timestamp:
                query = query.lt('timestamp', before_timestamp.isoformat())
            
            result = query.execute()
            messages = result.data if result.data else []
            
            # Return in chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Error getting recent messages: {str(e)}")
            return []
    
    async def get_message_by_whatsapp_id(self, whatsapp_message_id: str) -> Optional[Dict[str, Any]]:
        """Get a message by its WhatsApp message ID"""
        try:
            result = self.supabase.table('messages').select('*').eq('whatsapp_message_id', whatsapp_message_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting message by WhatsApp ID: {str(e)}")
            return None
    
    async def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Get a message by its database ID"""
        try:
            result = self.supabase.table('messages').select('*').eq('id', message_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting message by ID: {str(e)}")
            return None
    
    async def get_contact_by_id(self, contact_id: int) -> Optional[Dict[str, Any]]:
        """Get a contact by ID"""
        try:
            result = self.supabase.table('contacts').select('*').eq('id', contact_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting contact by ID: {str(e)}")
            return None
    
    async def store_message_embedding(
        self,
        message_id: int,
        text: str
    ):
        """Store message embedding"""
        try:
            # Generate embedding
            embedding = await self.embedding_generator.generate_embedding(text)
            
            # Store embedding
            embedding_data = {
                'message_id': message_id,
                'embedding_model': self.embedding_generator.model_name,
                'embedding_dimension': len(embedding),
                'embedding_vector': embedding.tolist()
            }
            
            result = self.supabase.table('message_embeddings').insert(embedding_data).execute()
            logger.info(f"Stored embedding for message: {message_id}")
            
        except Exception as e:
            logger.error(f"Error storing message embedding: {str(e)}")
    
    async def search_similar_messages(
        self,
        query_text: str,
        contact_id: int,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar messages using embeddings"""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_generator.generate_embedding(query_text)
            
            # Get all embeddings for this contact
            result = self.supabase.table('message_embeddings').select('*, messages(*)').eq('messages.contact_id', contact_id).execute()
            
            if not result.data:
                return []
            
            # Calculate similarities
            similarities = []
            for embedding_record in result.data:
                stored_embedding = np.array(embedding_record['embedding_vector'])
                similarity = self._cosine_similarity(query_embedding, stored_embedding)
                
                if similarity >= threshold:
                    similarities.append({
                        'message': embedding_record['messages'],
                        'similarity': similarity
                    })
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return [item['message'] for item in similarities[:limit]]
            
        except Exception as e:
            logger.error(f"Error searching similar messages: {str(e)}")
            return []
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    # Fact operations
    async def get_contact_facts(
        self,
        contact_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get facts for a contact"""
        try:
            query = self.supabase.table('facts').select('*').eq('contact_id', contact_id).order('last_reinforced', desc=True)
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting contact facts: {str(e)}")
            return []
    
    async def update_contact_facts(
        self,
        contact_id: int,
        new_facts: List[Dict[str, Any]],
        reinforced_facts: List[Dict[str, Any]],
        conflicted_facts: List[Dict[str, Any]],
        origin_message_id: int
    ):
        """Update contact facts"""
        try:
            # Insert new facts
            for fact in new_facts:
                fact_data = {
                    'contact_id': contact_id,
                    'user_id': 1,  # Default user ID
                    'key': fact['key'],
                    'value': fact['value'],
                    'origin_message_id': origin_message_id,
                    'extraction_confidence': fact.get('confidence', 1.0)
                }
                self.supabase.table('facts').insert(fact_data).execute()
            
            # Update reinforced facts
            for fact in reinforced_facts:
                self.supabase.table('facts').update({
                    'last_reinforced': datetime.utcnow().isoformat(),
                    'decay_weight': fact.get('decay_weight', 1.0),
                    'version': fact.get('version', 1) + 1
                }).eq('id', fact['id']).execute()
            
            logger.info(f"Updated facts for contact: {contact_id}")
            
        except Exception as e:
            logger.error(f"Error updating contact facts: {str(e)}")
    
    async def reinforce_fact(self, fact_id: int, decay_weight: float = 1.1):
        """Reinforce a specific fact"""
        try:
            self.supabase.table('facts').update({
                'last_reinforced': datetime.utcnow().isoformat(),
                'decay_weight': min(decay_weight, 2.0),  # Cap at 2.0
                'version': 1  # Increment version
            }).eq('id', fact_id).execute()
            logger.info(f"Reinforced fact: {fact_id}")
        except Exception as e:
            logger.error(f"Error reinforcing fact: {str(e)}")
    
    # Outbound reply operations
    async def store_outbound_reply(
        self,
        message_id: int,
        contact_id: int,
        user_id: int,
        reply_text: str,
        prompt_context: Dict[str, Any],
        meta_tags: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store the generated reply in database"""
        try:
            reply_data = {
                'message_id': message_id,
                'contact_id': contact_id,
                'user_id': user_id,
                'generated_text': reply_text,
                'full_prompt_context_json': prompt_context,
                'llm_meta_tags_json': meta_tags,
                'status': 'pending'  # Will be updated when sent
            }
            
            result = self.supabase.table('outbound_replies').insert(reply_data).execute()
            logger.info(f"Stored outbound reply for message: {message_id}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error storing outbound reply: {str(e)}")
            raise
    
    async def update_outbound_reply_status(
        self,
        reply_id: int,
        status: str,
        failure_reason: Optional[str] = None
    ):
        """Update the status of an outbound reply"""
        try:
            update_data = {'status': status}
            if failure_reason:
                update_data['failure_reason'] = failure_reason
            
            self.supabase.table('outbound_replies').update(update_data).eq('id', reply_id).execute()
            logger.info(f"Updated outbound reply status: {reply_id} -> {status}")
        except Exception as e:
            logger.error(f"Error updating outbound reply status: {str(e)}")
    
    # Progression stage operations
    async def get_contacts_by_stage(self, stage: str) -> List[Dict[str, Any]]:
        """Get all contacts at a specific progression stage"""
        try:
            result = self.supabase.table('contacts').select('*').eq('progression_stage', stage).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting contacts by stage: {str(e)}")
            return []
    
    async def get_contacts_needing_followup(self, hours_threshold: int = 24) -> List[Dict[str, Any]]:
        """Get contacts that need follow-up based on last interaction time"""
        try:
            threshold_time = datetime.utcnow() - timedelta(hours=hours_threshold)
            result = self.supabase.table('contacts').select('*').lt('last_inbound_message_at', threshold_time.isoformat()).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting contacts needing followup: {str(e)}")
            return [] 