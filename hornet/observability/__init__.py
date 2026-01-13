"""
Observability module with optional instrumentation.
Gracefully handles missing packages.
"""
import logging
import os
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Track what's available
_tracer = None
_metrics_enabled = False

def _try_import(module_name: str):
    """Try to import a module, return None if not available."""
    try:
        import importlib
        return importlib.import_module(module_name)
    except ImportError:
        logger.debug(f"Optional module {module_name} not available")
        return None

def init_observability(service_name: str = "hornet", **kwargs) -> None:
    """Initialize observability - works even without OpenTelemetry."""
    global _tracer, _metrics_enabled
    
    otel_enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    
    if not otel_enabled:
        logger.info("OpenTelemetry disabled (set OTEL_ENABLED=true to enable)")
        return
    
    # Try to set up OpenTelemetry
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        
        # Try OTLP exporter
        otlp = _try_import("opentelemetry.exporter.otlp.proto.grpc.trace_exporter")
        if otlp and os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            exporter = otlp.OTLPSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTLP exporter configured")
        
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
        logger.info("OpenTelemetry tracing initialized")
        
    except ImportError as e:
        logger.warning(f"OpenTelemetry not fully available: {e}")

def instrument_app(app) -> None:
    """Instrument FastAPI app - no-op if packages missing."""
    if os.getenv("OTEL_ENABLED", "false").lower() != "true":
        return
        
    # Try FastAPI instrumentation
    fastapi_inst = _try_import("opentelemetry.instrumentation.fastapi")
    if fastapi_inst:
        try:
            fastapi_inst.FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumented")
        except Exception as e:
            logger.debug(f"FastAPI instrumentation failed: {e}")
    
    # Try other instrumentations
    for name, instrumentor_class in [
        ("opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
        ("opentelemetry.instrumentation.redis", "RedisInstrumentor"),
        ("opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
    ]:
        mod = _try_import(name)
        if mod and hasattr(mod, instrumentor_class):
            try:
                getattr(mod, instrumentor_class)().instrument()
                logger.debug(f"{instrumentor_class} enabled")
            except Exception as e:
                logger.debug(f"{instrumentor_class} failed: {e}")

def get_tracer(name: str = "hornet"):
    """Get a tracer, returns no-op if not available."""
    global _tracer
    if _tracer:
        return _tracer
    
    # Return a no-op tracer
    class NoOpTracer:
        @contextmanager
        def start_as_current_span(self, name, **kwargs):
            yield None
        def start_span(self, name, **kwargs):
            return NoOpSpan()
    
    class NoOpSpan:
        def set_attribute(self, key, value): pass
        def set_status(self, status): pass
        def record_exception(self, exc): pass
        def end(self): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    
    return NoOpTracer()

# Convenience exports
tracer = get_tracer()



