"""
HORNET Observability
OpenTelemetry tracing and structured logging configuration.
"""
import os
import sys
import logging
from typing import Optional
import structlog

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat


# ============================================================================
# STRUCTURED LOGGING
# ============================================================================

def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    add_timestamp: bool = True,
):
    """Configure structured logging with structlog."""
    
    # Shared processors for all loggers
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso") if add_timestamp else lambda *a, **k: a[2],
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_output:
        # JSON output for production
        renderer = structlog.processors.JSONRenderer()
    else:
        # Pretty output for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure stdlib logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Quiet noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return structlog.get_logger()


def get_logger(name: str = None):
    """Get a structured logger."""
    return structlog.get_logger(name)


# ============================================================================
# OPENTELEMETRY TRACING
# ============================================================================

_tracer: Optional[trace.Tracer] = None


def configure_tracing(
    service_name: str = "hornet",
    environment: str = "development",
    otlp_endpoint: str = None,
):
    """Configure OpenTelemetry tracing."""
    global _tracer
    
    # Create resource with service info
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "2.0.0",
        "deployment.environment": environment,
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add exporters
    if otlp_endpoint:
        # OTLP exporter for production (Jaeger, Tempo, etc.)
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except ImportError:
            pass
    
    if environment == "development":
        # Console exporter for development
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    
    # Configure propagation (B3 for compatibility)
    set_global_textmap(B3MultiFormat())
    
    # Get tracer
    _tracer = trace.get_tracer(service_name)
    
    return _tracer


def get_tracer() -> trace.Tracer:
    """Get the configured tracer."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer("hornet")
    return _tracer


def instrument_app(app):
    """Instrument FastAPI app with OpenTelemetry."""
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()


# ============================================================================
# TRACE CONTEXT HELPERS
# ============================================================================

class TraceContext:
    """Context manager for creating spans."""
    
    def __init__(self, name: str, attributes: dict = None):
        self.name = name
        self.attributes = attributes or {}
        self.span = None
    
    def __enter__(self):
        tracer = get_tracer()
        self.span = tracer.start_span(self.name)
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.span.record_exception(exc_val)
            self.span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
        self.span.end()
        return False


def trace_span(name: str, attributes: dict = None):
    """Decorator to trace a function."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with TraceContext(name, attributes) as span:
                span.set_attribute("function", func.__name__)
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            with TraceContext(name, attributes) as span:
                span.set_attribute("function", func.__name__)
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# ============================================================================
# AGENT TRACING
# ============================================================================

def trace_agent_call(agent_name: str, incident_id: str = None):
    """Create a span for an agent call."""
    tracer = get_tracer()
    span = tracer.start_span(f"agent.{agent_name}")
    span.set_attribute("agent.name", agent_name)
    if incident_id:
        span.set_attribute("incident.id", incident_id)
    return span


def trace_llm_call(model: str, tokens: int = 0):
    """Create a span for an LLM call."""
    tracer = get_tracer()
    span = tracer.start_span("llm.call")
    span.set_attribute("llm.model", model)
    span.set_attribute("llm.tokens", tokens)
    return span


# ============================================================================
# INITIALIZATION
# ============================================================================

def init_observability(
    service_name: str = "hornet",
    environment: str = None,
    log_level: str = None,
    otlp_endpoint: str = None,
):
    """Initialize all observability components."""
    env = environment or os.getenv("ENVIRONMENT", "development")
    level = log_level or os.getenv("LOG_LEVEL", "INFO")
    endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT")
    
    # Configure logging
    logger = configure_logging(
        level=level,
        json_output=(env == "production"),
    )
    
    # Configure tracing
    configure_tracing(
        service_name=service_name,
        environment=env,
        otlp_endpoint=endpoint,
    )
    
    logger.info(
        "observability_initialized",
        service=service_name,
        environment=env,
        log_level=level,
        tracing_enabled=bool(endpoint),
    )
    
    return logger
