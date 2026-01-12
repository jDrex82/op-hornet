"""HORNET OpenTelemetry Tracing"""
import asyncio
from typing import Dict, Any
from functools import wraps
import structlog

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Status, StatusCode

logger = structlog.get_logger()

def setup_tracing(service_name: str = "hornet", otlp_endpoint: str = None) -> trace.Tracer:
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
        except ImportError:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

tracer = trace.get_tracer("hornet")

def traced(name: str = None):
    def decorator(func):
        span_name = name or func.__name__
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            return wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            return wrapper
    return decorator

def add_span_attributes(attrs: Dict[str, Any]):
    span = trace.get_current_span()
    if span:
        for k, v in attrs.items():
            span.set_attribute(k, v)
