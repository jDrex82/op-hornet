"""Test embedding pipeline."""
import pytest
from hornet.embedding import EmbeddingPipeline, EmbeddingCache


def test_embedding_cache():
    cache = EmbeddingCache(max_size=3)
    
    cache.set("text1", [0.1, 0.2])
    cache.set("text2", [0.3, 0.4])
    
    assert cache.get("text1") == [0.1, 0.2]
    assert cache.get("text2") == [0.3, 0.4]
    assert cache.get("text3") is None


def test_embedding_cache_eviction():
    cache = EmbeddingCache(max_size=2)
    
    cache.set("text1", [0.1])
    cache.set("text2", [0.2])
    cache.set("text3", [0.3])  # Should evict text1
    
    assert cache.get("text1") is None
    assert cache.get("text2") == [0.2]
    assert cache.get("text3") == [0.3]


def test_format_event_for_embedding():
    pipeline = EmbeddingPipeline()
    
    event = {
        "event_type": "auth.brute_force",
        "severity": "HIGH",
        "entities": [{"type": "ip", "value": "192.168.1.1"}],
        "raw_payload": {"source": "firewall"},
    }
    
    result = pipeline.format_event_for_embedding(event)
    
    assert "type:auth.brute_force" in result
    assert "severity:HIGH" in result
    assert "ip:192.168.1.1" in result
