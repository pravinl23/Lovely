"""
Main application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import signal
import sys

from src.api_control_plane.webhook_handler import router as webhook_router
from src.api_control_plane.dashboard import router as dashboard_router
from src.core.message_queue import MessageQueue
from src.perception_layer.message_processor import MessageProcessor
from src.cognition_layer.orchestrator import CognitiveOrchestrator
from src.utils.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)

# Global references for cleanup
message_queue = None
running_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global message_queue, running_tasks
    
    logger.info("Starting WhatsApp Automation System...")
    
    # Initialize message queue
    message_queue = MessageQueue()
    await message_queue.connect()
    
    # Register consumers
    await register_consumers(message_queue)
    
    # Start consumer tasks
    consumer_task = asyncio.create_task(message_queue.start_consumers())
    running_tasks.append(consumer_task)
    
    logger.info("Application started successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down application...")
    
    # Stop consumers
    await message_queue.stop_consumers()
    
    # Cancel running tasks
    for task in running_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Disconnect from queue
    await message_queue.disconnect()
    
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="WhatsApp Automation API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhook_router)
app.include_router(dashboard_router)


async def register_consumers(queue: MessageQueue):
    """Register all message queue consumers"""
    
    # Perception layer consumer
    async def process_perception_message(queue_message):
        async with MessageProcessor() as processor:
            await processor.process_incoming_message(queue_message)
    
    await queue.register_consumer("incoming_messages", process_perception_message)
    
    # Cognition layer consumer
    async def process_cognition_message(queue_message):
        async with CognitiveOrchestrator() as orchestrator:
            await orchestrator.process_cognitive_task(queue_message)
    
    await queue.register_consumer("cognition_tasks", process_cognition_message)
    
    # Status update consumer (simplified)
    async def process_status_update(queue_message):
        logger.info(f"Message status update: {queue_message.data}")
    
    await queue.register_consumer("status_updates", process_status_update)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "WhatsApp Automation System",
        "status": "operational",
        "version": "1.0.0",
        "dashboard": "/dashboard"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


def handle_signal(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 