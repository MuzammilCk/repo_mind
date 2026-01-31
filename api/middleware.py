"""
API Middleware
CORS, rate limiting, request ID tracking, and logging
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
import uuid
import logging

from utils.logger import set_request_id, clear_request_id, get_logger
from utils.metrics import metrics_collector

logger = get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def setup_middleware(app: FastAPI):
    """
    Configure all middleware for the application
    """
    
    # 1. Request ID Middleware (first - sets context for all subsequent middleware)
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """
        Add unique request ID to each request
        """
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        
        # Set in logging context
        set_request_id(request_id)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Clear request ID from context
            clear_request_id()
    
    # 2. Logging Middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """
        Log all requests and responses
        """
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            "Request completed",
            extra={
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2)
            }
        )
        
        # Record metrics
        metrics_collector.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response
    
    # 3. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 4. Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    logger.info("Middleware configured: Request ID, Logging, CORS, Rate Limiting")
