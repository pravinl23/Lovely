"""
Message Queue implementation for asynchronous processing
"""
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import redis.asyncio as redis
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class QueuePriority(Enum):
    """Priority levels for queue messages"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    DEFERRED = 5


@dataclass
class QueueMessage:
    """Message structure for the queue"""
    id: str
    queue_name: str
    data: Dict[str, Any]
    priority: int
    created_at: str
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueMessage":
        return cls(**data)


class MessageQueue:
    """Redis-backed message queue for async processing"""
    
    def __init__(self):
        self.redis_url = settings.redis_url
        self.redis_client = None
        self._consumers = {}
        self._running = False
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Connected to Redis message queue")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis message queue")
    
    async def enqueue(
        self, 
        queue_name: str, 
        data: Dict[str, Any],
        priority: int = QueuePriority.NORMAL.value
    ) -> str:
        """Add a message to the queue"""
        await self.connect()
        
        message = QueueMessage(
            id=str(uuid.uuid4()),
            queue_name=queue_name,
            data=data,
            priority=priority,
            created_at=datetime.utcnow().isoformat()
        )
        
        # Use sorted set for priority queue
        queue_key = f"queue:{queue_name}"
        score = priority  # Lower score = higher priority
        
        await self.redis_client.zadd(
            queue_key,
            {json.dumps(message.to_dict()): score}
        )
        
        logger.info(f"Message enqueued", extra={
            "queue": queue_name,
            "message_id": message.id,
            "priority": priority
        })
        
        return message.id
    
    async def dequeue(
        self, 
        queue_name: str,
        timeout: Optional[int] = None
    ) -> Optional[QueueMessage]:
        """Get the next message from the queue"""
        await self.connect()
        
        queue_key = f"queue:{queue_name}"
        processing_key = f"processing:{queue_name}"
        
        # Use Lua script for atomic dequeue operation
        lua_script = """
        local queue_key = KEYS[1]
        local processing_key = KEYS[2]
        local timestamp = ARGV[1]
        
        local messages = redis.call('zrange', queue_key, 0, 0)
        if #messages == 0 then
            return nil
        end
        
        local message = messages[1]
        redis.call('zrem', queue_key, message)
        redis.call('hset', processing_key, message, timestamp)
        
        return message
        """
        
        result = await self.redis_client.eval(
            lua_script,
            2,
            queue_key,
            processing_key,
            datetime.utcnow().isoformat()
        )
        
        if result:
            message_data = json.loads(result)
            return QueueMessage.from_dict(message_data)
        
        return None
    
    async def acknowledge(
        self, 
        queue_name: str, 
        message: QueueMessage
    ):
        """Acknowledge successful processing of a message"""
        await self.connect()
        
        processing_key = f"processing:{queue_name}"
        await self.redis_client.hdel(
            processing_key,
            json.dumps(message.to_dict())
        )
        
        logger.debug(f"Message acknowledged", extra={
            "queue": queue_name,
            "message_id": message.id
        })
    
    async def requeue(
        self, 
        queue_name: str, 
        message: QueueMessage,
        delay_seconds: int = 0
    ):
        """Requeue a failed message"""
        await self.connect()
        
        processing_key = f"processing:{queue_name}"
        await self.redis_client.hdel(
            processing_key,
            json.dumps(message.to_dict())
        )
        
        # Increment retry count
        message.retry_count += 1
        
        if message.retry_count > message.max_retries:
            # Move to dead letter queue
            dlq_key = f"dlq:{queue_name}"
            await self.redis_client.rpush(
                dlq_key,
                json.dumps(message.to_dict())
            )
            
            logger.error(f"Message moved to DLQ after max retries", extra={
                "queue": queue_name,
                "message_id": message.id,
                "retry_count": message.retry_count
            })
            return
        
        # Requeue with delay if specified
        if delay_seconds > 0:
            delayed_key = f"delayed:{queue_name}"
            score = datetime.utcnow().timestamp() + delay_seconds
            
            await self.redis_client.zadd(
                delayed_key,
                {json.dumps(message.to_dict()): score}
            )
        else:
            # Requeue immediately with lower priority
            await self.enqueue(
                queue_name,
                message.data,
                priority=min(message.priority + 1, QueuePriority.DEFERRED.value)
            )
        
        logger.warning(f"Message requeued", extra={
            "queue": queue_name,
            "message_id": message.id,
            "retry_count": message.retry_count,
            "delay_seconds": delay_seconds
        })
    
    async def register_consumer(
        self,
        queue_name: str,
        handler: Callable[[QueueMessage], Any]
    ):
        """Register a consumer function for a queue"""
        self._consumers[queue_name] = handler
        logger.info(f"Consumer registered for queue: {queue_name}")
    
    async def start_consumers(self):
        """Start all registered consumers"""
        self._running = True
        await self.connect()
        
        # Start delayed message processor
        asyncio.create_task(self._process_delayed_messages())
        
        # Start consumer tasks
        tasks = []
        for queue_name, handler in self._consumers.items():
            task = asyncio.create_task(
                self._consume_messages(queue_name, handler)
            )
            tasks.append(task)
        
        logger.info(f"Started {len(tasks)} consumer tasks")
        
        # Wait for all consumers
        await asyncio.gather(*tasks)
    
    async def stop_consumers(self):
        """Stop all consumers"""
        self._running = False
        logger.info("Stopping consumers...")
    
    async def _consume_messages(
        self,
        queue_name: str,
        handler: Callable[[QueueMessage], Any]
    ):
        """Consumer loop for a specific queue"""
        logger.info(f"Starting consumer for queue: {queue_name}")
        
        while self._running:
            try:
                # Get next message
                message = await self.dequeue(queue_name)
                
                if not message:
                    # No messages, wait a bit
                    await asyncio.sleep(0.1)
                    continue
                
                # Process message
                try:
                    await handler(message)
                    await self.acknowledge(queue_name, message)
                    
                except Exception as e:
                    logger.error(
                        f"Error processing message",
                        extra={
                            "queue": queue_name,
                            "message_id": message.id,
                            "error": str(e)
                        },
                        exc_info=True
                    )
                    
                    # Requeue with exponential backoff
                    delay = 2 ** message.retry_count
                    await self.requeue(queue_name, message, delay)
                    
            except Exception as e:
                logger.error(
                    f"Consumer error",
                    extra={
                        "queue": queue_name,
                        "error": str(e)
                    },
                    exc_info=True
                )
                await asyncio.sleep(1)
    
    async def _process_delayed_messages(self):
        """Process delayed messages that are ready"""
        while self._running:
            try:
                await self.connect()
                
                # Get all delayed queues
                delayed_keys = await self.redis_client.keys("delayed:*")
                
                for delayed_key in delayed_keys:
                    # Get messages that are ready
                    now = datetime.utcnow().timestamp()
                    messages = await self.redis_client.zrangebyscore(
                        delayed_key,
                        0,
                        now
                    )
                    
                    for message_json in messages:
                        # Remove from delayed queue
                        await self.redis_client.zrem(delayed_key, message_json)
                        
                        # Parse and requeue
                        message = QueueMessage.from_dict(json.loads(message_json))
                        queue_name = delayed_key.replace("delayed:", "")
                        
                        await self.enqueue(
                            queue_name,
                            message.data,
                            priority=message.priority
                        )
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(
                    "Error processing delayed messages",
                    extra={"error": str(e)},
                    exc_info=True
                )
                await asyncio.sleep(5)
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Get statistics for a queue"""
        await self.connect()
        
        queue_key = f"queue:{queue_name}"
        processing_key = f"processing:{queue_name}"
        dlq_key = f"dlq:{queue_name}"
        delayed_key = f"delayed:{queue_name}"
        
        stats = {
            "queue_name": queue_name,
            "pending": await self.redis_client.zcard(queue_key),
            "processing": await self.redis_client.hlen(processing_key),
            "dead_letter": await self.redis_client.llen(dlq_key),
            "delayed": await self.redis_client.zcard(delayed_key)
        }
        
        return stats 