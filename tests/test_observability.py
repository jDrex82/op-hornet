"""Test observability module."""
import pytest
from hornet.observability import configure_logging, get_logger, TraceContext


class TestLogging:
    def test_configure_logging(self):
        logger = configure_logging(level="DEBUG", json_output=False)
        assert logger is not None
    
    def test_get_logger(self):
        logger = get_logger("test")
        assert logger is not None


class TestTracing:
    def test_trace_context(self):
        with TraceContext("test_span", {"key": "value"}) as span:
            assert span is not None
