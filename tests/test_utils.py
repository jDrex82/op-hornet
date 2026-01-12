"""Test HORNET utilities."""
import pytest
from hornet.utils import (
    sanitize_input, calculate_impact_score, calculate_priority_score,
    merge_confidence, calculate_zscore, extract_entities,
)

def test_sanitize_input_normal():
    result = sanitize_input("Hello world")
    assert result == "Hello world"

def test_sanitize_input_truncate():
    long_input = "x" * 20000
    result = sanitize_input(long_input, max_length=1000)
    assert len(result) == 1000

def test_sanitize_input_control_chars():
    result = sanitize_input("Hello\x00World")
    assert "\x00" not in result

def test_calculate_impact_score():
    score = calculate_impact_score(1.0, 1.0, 1.0, 1.0)
    assert score == 1.0
    
    score = calculate_impact_score(0.5, 0.5, 0.5, 0.5)
    assert score == 0.5

def test_calculate_priority_score():
    score = calculate_priority_score(0.9, "CRITICAL", 0.9, 0.5)
    assert score > 0.8

def test_merge_confidence():
    result = merge_confidence([0.8, 0.7])
    assert 0.9 < result < 1.0  # Should be high but not 1.0

def test_merge_confidence_empty():
    result = merge_confidence([])
    assert result == 0.0

def test_calculate_zscore():
    z = calculate_zscore(100, 50, 10)
    assert z == 5.0

def test_extract_entities():
    payload = {"message": "Connection from 192.168.1.100 to example.com"}
    entities = extract_entities(payload)
    assert any(e["type"] == "ip" and e["value"] == "192.168.1.100" for e in entities)
