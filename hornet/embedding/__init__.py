"""
HORNET Embedding Pipeline
Vector embeddings for similarity search using OpenAI text-embedding-3-small.
"""
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import json
import structlog
from openai import AsyncOpenAI
import numpy as np

from hornet.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class EmbeddingResult:
    text: str
    embedding: List[float]
    model: str
    tokens_used: int
    cached: bool = False


class EmbeddingCache:
    """LRU cache for embeddings to avoid redundant API calls."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache: Dict[str, List[float]] = {}
        self._access_order: List[str] = []
    
    def _hash_text(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        key = self._hash_text(text)
        if key in self._cache:
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None
    
    def set(self, text: str, embedding: List[float]):
        key = self._hash_text(text)
        if len(self._cache) >= self.max_size:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = embedding
        self._access_order.append(key)


class EmbeddingPipeline:
    """
    Embedding pipeline for HORNET.
    
    Uses OpenAI text-embedding-3-small (1536 dimensions).
    Supports batching for efficiency.
    """
    
    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    MAX_TOKENS = 8191
    BATCH_SIZE = 100
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.cache = EmbeddingCache()
        self._rate_limiter = asyncio.Semaphore(50)  # Max concurrent requests
    
    async def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single text string."""
        # Check cache
        cached = self.cache.get(text)
        if cached:
            return EmbeddingResult(
                text=text,
                embedding=cached,
                model=self.MODEL,
                tokens_used=0,
                cached=True,
            )
        
        async with self._rate_limiter:
            try:
                response = await self.client.embeddings.create(
                    model=self.MODEL,
                    input=text,
                    dimensions=self.DIMENSIONS,
                )
                
                embedding = response.data[0].embedding
                tokens_used = response.usage.total_tokens
                
                self.cache.set(text, embedding)
                
                return EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    model=self.MODEL,
                    tokens_used=tokens_used,
                )
            except Exception as e:
                logger.error("embedding_failed", error=str(e), text_length=len(text))
                raise
    
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Embed multiple texts in batches."""
        results = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache first
        for i, text in enumerate(texts):
            cached = self.cache.get(text)
            if cached:
                results.append(EmbeddingResult(
                    text=text,
                    embedding=cached,
                    model=self.MODEL,
                    tokens_used=0,
                    cached=True,
                ))
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Batch embed uncached texts
        for batch_start in range(0, len(uncached_texts), self.BATCH_SIZE):
            batch = uncached_texts[batch_start:batch_start + self.BATCH_SIZE]
            batch_indices = uncached_indices[batch_start:batch_start + self.BATCH_SIZE]
            
            async with self._rate_limiter:
                try:
                    response = await self.client.embeddings.create(
                        model=self.MODEL,
                        input=batch,
                        dimensions=self.DIMENSIONS,
                    )
                    
                    for j, data in enumerate(response.data):
                        idx = batch_indices[j]
                        text = batch[j]
                        embedding = data.embedding
                        
                        self.cache.set(text, embedding)
                        
                        results[idx] = EmbeddingResult(
                            text=text,
                            embedding=embedding,
                            model=self.MODEL,
                            tokens_used=response.usage.total_tokens // len(batch),
                        )
                except Exception as e:
                    logger.error("batch_embedding_failed", error=str(e), batch_size=len(batch))
                    raise
        
        return results
    
    def format_event_for_embedding(self, event: Dict[str, Any]) -> str:
        """Format an event for embedding."""
        parts = [
            f"type:{event.get('event_type', 'unknown')}",
            f"severity:{event.get('severity', 'unknown')}",
        ]
        
        # Add entities
        for entity in event.get('entities', [])[:5]:
            parts.append(f"{entity.get('type')}:{entity.get('value')}")
        
        # Add truncated payload
        payload = json.dumps(event.get('raw_payload', {}))[:500]
        parts.append(f"payload:{payload}")
        
        return " ".join(parts)
    
    def format_pattern_for_embedding(self, pattern: Dict[str, Any]) -> str:
        """Format a pattern for embedding."""
        parts = [
            f"name:{pattern.get('name', '')}",
            f"description:{pattern.get('description', '')}",
        ]
        
        for technique in pattern.get('mitre_techniques', []):
            parts.append(f"mitre:{technique}")
        
        return " ".join(parts)
    
    def format_incident_for_embedding(self, incident: Dict[str, Any]) -> str:
        """Format an incident summary for embedding."""
        parts = [
            f"summary:{incident.get('summary', '')}",
            f"severity:{incident.get('severity', '')}",
            f"outcome:{incident.get('outcome', '')}",
        ]
        
        for finding in incident.get('key_findings', [])[:3]:
            parts.append(f"finding:{finding}")
        
        return " ".join(parts)


class SimilaritySearch:
    """
    Similarity search using pgvector.
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.pipeline = EmbeddingPipeline()
    
    async def find_similar_events(
        self,
        query_text: str,
        tenant_id: str,
        limit: int = 10,
        min_similarity: float = 0.7,
        time_window_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Find similar events using cosine similarity."""
        # Get query embedding
        result = await self.pipeline.embed_text(query_text)
        query_embedding = result.embedding
        
        # Query using pgvector
        # Note: This would use actual SQLAlchemy query in production
        sql = """
        SELECT id, event_type, severity, entities, timestamp,
               1 - (embedding <=> :query_embedding) as similarity
        FROM events
        WHERE tenant_id = :tenant_id
          AND timestamp > NOW() - INTERVAL ':days days'
          AND embedding IS NOT NULL
        ORDER BY embedding <=> :query_embedding
        LIMIT :limit
        """
        
        # Placeholder - would execute actual query
        return []
    
    async def find_similar_patterns(
        self,
        query_text: str,
        tenant_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find similar attack patterns."""
        result = await self.pipeline.embed_text(query_text)
        query_embedding = result.embedding
        
        # Query patterns table
        return []
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_np = np.array(a)
        b_np = np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


# Global pipeline instance
embedding_pipeline = EmbeddingPipeline()
