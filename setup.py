"""HORNET package setup."""
from setuptools import setup, find_packages

setup(
    name="hornet",
    version="2.0.0",
    description="HORNET - Autonomous SOC Swarm",
    author="HORNET Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "pydantic>=2.5.0",
        "sqlalchemy>=2.0.25",
        "asyncpg>=0.29.0",
        "redis>=5.0.1",
        "anthropic>=0.18.0",
        "openai>=1.10.0",
        "httpx>=0.26.0",
        "structlog>=24.1.0",
    ],
    entry_points={
        "console_scripts": [
            "hornet=hornet.cli:main",
        ],
    },
)
