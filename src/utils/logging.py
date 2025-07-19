"""
Structured logging configuration
"""
import structlog
import logging
import sys
from typing import Any, Dict
from config.settings import settings


def configure_logging():
    """Configure structured logging for the application"""
    
    # Set log level based on settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ] + (
            [structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            )] if settings.debug else []
        ) + (
            [structlog.processors.dict_tracebacks] if settings.debug else []
        ) + [
            structlog.dev.ConsoleRenderer() if settings.environment == "development" 
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


def log_performance(func):
    """Decorator to log function performance"""
    import time
    import functools
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.info(
                "Function executed successfully",
                function=func.__name__,
                duration_seconds=round(duration, 3),
                args_count=len(args),
                kwargs_count=len(kwargs)
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Function execution failed",
                function=func.__name__,
                duration_seconds=round(duration, 3),
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.info(
                "Function executed successfully",
                function=func.__name__,
                duration_seconds=round(duration, 3),
                args_count=len(args),
                kwargs_count=len(kwargs)
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Function execution failed",
                function=func.__name__,
                duration_seconds=round(duration, 3),
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            raise
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Initialize logging when module is imported
configure_logging() 