"""Integration test configuration."""
import os
import pytest

# Set test environment variables
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
