"""
HORNET Utilities
Common utilities and helpers.
"""
import re
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()


# Prompt injection defense patterns
INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|your)\s+instructions?",
    r"system\s*prompt",
    r"you\s+are\s+now",
    r"disregard\s+(all\s+)?instructions?",
    r"forget\s+(your|all)\s+instructions?",
    r"new\s+instructions?",
    r"override\s+(system|safety)",
    r"jailbreak",
    r"DAN\s+mode",
    r"\[system\]",
    r"<\|im_start\|>",
]


def sanitize_input(text: str, max_length: int = 10240) -> str:
    """Sanitize input to prevent prompt injection."""
    if not text:
        return ""
    
    # Truncate oversized input
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning("input_truncated", original_length=len(text), max_length=max_length)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Check for injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning("potential_injection_detected", pattern=pattern)
            # Don't remove, just log - let the agent handle it
    
    return text


def calculate_impact_score(
    asset_criticality: float,
    data_sensitivity: float,
    user_privilege: float,
    blast_radius: float,
) -> float:
    """
    Calculate impact score using weighted formula.
    impact = (asset_crit × 0.35) + (data_sens × 0.25) + (user_priv × 0.20) + (blast × 0.20)
    """
    return (
        asset_criticality * 0.35 +
        data_sensitivity * 0.25 +
        user_privilege * 0.20 +
        blast_radius * 0.20
    )


def calculate_priority_score(
    confidence: float,
    severity: str,
    impact: float,
    recency_hours: float,
) -> float:
    """
    Calculate priority score for incident queue.
    priority = (confidence × 0.30) + (severity_weight × 0.25) + (impact × 0.25) + (recency × 0.20)
    """
    severity_weights = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.50, "LOW": 0.25}
    severity_weight = severity_weights.get(severity.upper(), 0.25)
    
    # Recency: 1.0 for < 1 hour, decays to 0 over 24 hours
    recency = max(0, 1.0 - (recency_hours / 24))
    
    return (
        confidence * 0.30 +
        severity_weight * 0.25 +
        impact * 0.25 +
        recency * 0.20
    )


def merge_confidence(confidences: List[float], weights: List[float] = None) -> float:
    """
    Merge multiple confidence scores.
    merged_confidence = 1 - Π(1 - c_i * w_i)
    """
    if not confidences:
        return 0.0
    
    if weights is None:
        weights = [1.0] * len(confidences)
    
    product = 1.0
    for c, w in zip(confidences, weights):
        product *= (1 - c * w)
    
    return 1 - product


def calculate_zscore(value: float, mean: float, std: float) -> float:
    """Calculate z-score for anomaly detection."""
    if std == 0:
        return 0.0
    return (value - mean) / std


def hash_api_key(api_key: str) -> str:
    """Hash API key for storage."""
    import bcrypt
    return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()


def verify_api_key(api_key: str, hashed: str) -> bool:
    """Verify API key against hash."""
    import bcrypt
    return bcrypt.checkpw(api_key.encode(), hashed.encode())


def generate_api_key() -> str:
    """Generate a new API key."""
    import secrets
    return f"hnt_{secrets.token_urlsafe(32)}"


def extract_entities(raw_payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract entities from raw event payload."""
    entities = []
    
    # IP patterns
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Domain pattern
    domain_pattern = r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b'
    
    # Hash patterns (MD5, SHA1, SHA256)
    hash_patterns = [
        (r'\b[a-fA-F0-9]{32}\b', 'md5'),
        (r'\b[a-fA-F0-9]{40}\b', 'sha1'),
        (r'\b[a-fA-F0-9]{64}\b', 'sha256'),
    ]
    
    text = str(raw_payload)
    
    for ip in set(re.findall(ip_pattern, text)):
        entities.append({"type": "ip", "value": ip})
    
    for email in set(re.findall(email_pattern, text)):
        entities.append({"type": "email", "value": email})
    
    for domain in set(re.findall(domain_pattern, text, re.IGNORECASE)):
        if domain not in ['example.com', 'localhost']:
            entities.append({"type": "domain", "value": domain})
    
    for pattern, hash_type in hash_patterns:
        for h in set(re.findall(pattern, text)):
            entities.append({"type": "hash", "value": h, "hash_type": hash_type})
    
    return entities


class TokenBudgetTracker:
    """Track and enforce token budgets."""
    
    def __init__(self, budget: int = 50000):
        self.budget = budget
        self.used = 0
    
    def can_spend(self, tokens: int) -> bool:
        return self.used + tokens <= self.budget
    
    def spend(self, tokens: int) -> bool:
        if self.can_spend(tokens):
            self.used += tokens
            return True
        return False
    
    @property
    def remaining(self) -> int:
        return self.budget - self.used
    
    @property
    def percentage_used(self) -> float:
        return self.used / self.budget
    
    @property
    def status(self) -> str:
        pct = self.percentage_used
        if pct >= 0.95:
            return "CRITICAL"
        elif pct >= 0.90:
            return "FORCE_TRANSITION"
        elif pct >= 0.80:
            return "WARNING"
        return "OK"
