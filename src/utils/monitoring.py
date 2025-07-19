"""
Monitoring and metrics utilities
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import asyncio
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Define metrics
messages_received = Counter(
    'whatsapp_messages_received_total',
    'Total number of messages received',
    ['message_type', 'contact_id']
)

messages_sent = Counter(
    'whatsapp_messages_sent_total',
    'Total number of messages sent',
    ['status']
)

message_processing_time = Histogram(
    'whatsapp_message_processing_seconds',
    'Time spent processing messages',
    ['stage']
)

active_conversations = Gauge(
    'whatsapp_active_conversations',
    'Number of active conversations'
)

api_errors = Counter(
    'whatsapp_api_errors_total',
    'Total number of API errors',
    ['error_type']
)


async def start_metrics_server(port: int = 9090):
    """Start Prometheus metrics server"""
    try:
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
        
        # Keep the server running
        while True:
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"Failed to start metrics server: {str(e)}") 