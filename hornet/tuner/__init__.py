"""
HORNET Tuner Feedback Loop
Automatic threshold adjustment based on human feedback.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import asyncio
import structlog

logger = structlog.get_logger()


class FeedbackType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"
    ESCALATE = "ESCALATE"
    MISSED = "MISSED"


@dataclass
class FeedbackRecord:
    incident_id: str
    agent_name: str
    feedback_type: FeedbackType
    original_confidence: float
    user_id: str
    timestamp: datetime
    justification: str = ""


@dataclass
class AgentMetrics:
    agent_name: str
    period_start: datetime
    period_end: datetime
    total_findings: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0


@dataclass
class ThresholdAdjustment:
    agent_name: str
    threshold_type: str
    current_value: float
    recommended_value: float
    change_percent: float
    justification: str
    confidence: float
    sample_size: int


class TunerFeedbackLoop:
    MIN_SAMPLES = 50
    MAX_ADJUSTMENT = 0.10
    WINDOW_DAYS = 7
    MIN_THRESHOLDS = {"DISMISS": 0.20, "INVESTIGATE": 0.50, "CONFIRM": 0.70}
    TARGET_PRECISION = 0.80
    TARGET_RECALL = 0.95
    
    def __init__(self):
        self._feedback: List[FeedbackRecord] = []
        self._thresholds: Dict[str, Dict[str, float]] = {}
        self._running = False
    
    async def record_feedback(self, incident_id: str, agent_name: str, feedback_type: FeedbackType, confidence: float, user_id: str, justification: str = ""):
        record = FeedbackRecord(incident_id=incident_id, agent_name=agent_name, feedback_type=feedback_type, original_confidence=confidence, user_id=user_id, timestamp=datetime.utcnow(), justification=justification)
        self._feedback.append(record)
        logger.info("feedback_recorded", agent=agent_name, type=feedback_type.value)
        return record
    
    async def calculate_metrics(self, agent_name: str) -> AgentMetrics:
        cutoff = datetime.utcnow() - timedelta(days=self.WINDOW_DAYS)
        relevant = [f for f in self._feedback if f.agent_name == agent_name and f.timestamp >= cutoff]
        if not relevant:
            return AgentMetrics(agent_name=agent_name, period_start=cutoff, period_end=datetime.utcnow())
        tp = sum(1 for f in relevant if f.feedback_type == FeedbackType.APPROVE)
        fp = sum(1 for f in relevant if f.feedback_type == FeedbackType.REJECT)
        fn = sum(1 for f in relevant if f.feedback_type == FeedbackType.MISSED)
        total = tp + fp
        precision = tp / total if total > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        return AgentMetrics(agent_name=agent_name, period_start=cutoff, period_end=datetime.utcnow(), total_findings=total, true_positives=tp, false_positives=fp, false_negatives=fn, precision=precision, recall=recall, f1_score=f1)
    
    async def calculate_adjustment(self, agent_name: str, metrics: AgentMetrics) -> Optional[ThresholdAdjustment]:
        if metrics.total_findings < self.MIN_SAMPLES:
            return None
        current = self._thresholds.get(agent_name, {}).get("confidence", 0.5)
        if metrics.precision < self.TARGET_PRECISION:
            adj = min((metrics.false_positives / metrics.total_findings) * 0.5, self.MAX_ADJUSTMENT)
            new = min(current + adj, 0.95)
            reason = f"Raising threshold: precision={metrics.precision:.0%}"
        elif metrics.recall < self.TARGET_RECALL and metrics.false_negatives > 0:
            adj = min((metrics.false_negatives / (metrics.true_positives + metrics.false_negatives)) * 0.3, self.MAX_ADJUSTMENT)
            new = max(current - adj, self.MIN_THRESHOLDS["INVESTIGATE"])
            reason = f"Lowering threshold: recall={metrics.recall:.0%}"
        else:
            return None
        return ThresholdAdjustment(agent_name=agent_name, threshold_type="confidence", current_value=current, recommended_value=new, change_percent=(new - current) / current if current > 0 else 0, justification=reason, confidence=min(metrics.total_findings / 100, 1.0), sample_size=metrics.total_findings)
    
    async def apply_adjustment(self, adj: ThresholdAdjustment, auto: bool = False) -> bool:
        if not auto:
            logger.info("adjustment_queued", agent=adj.agent_name, current=adj.current_value, recommended=adj.recommended_value)
            return False
        if adj.agent_name not in self._thresholds:
            self._thresholds[adj.agent_name] = {}
        self._thresholds[adj.agent_name][adj.threshold_type] = adj.recommended_value
        logger.info("adjustment_applied", agent=adj.agent_name, new_value=adj.recommended_value)
        return True
    
    async def run_cycle(self) -> List[ThresholdAdjustment]:
        agents = set(f.agent_name for f in self._feedback)
        adjustments = []
        for agent in agents:
            metrics = await self.calculate_metrics(agent)
            if metrics.total_findings >= self.MIN_SAMPLES:
                adj = await self.calculate_adjustment(agent, metrics)
                if adj:
                    adjustments.append(adj)
        return adjustments
    
    async def start_loop(self, interval_hours: int = 24):
        self._running = True
        while self._running:
            try:
                adjs = await self.run_cycle()
                for adj in adjs:
                    if adj.confidence >= 0.8 and abs(adj.change_percent) <= 0.05:
                        await self.apply_adjustment(adj, auto=True)
            except Exception as e:
                logger.error("tuner_error", error=str(e))
            await asyncio.sleep(interval_hours * 3600)
    
    def stop_loop(self):
        self._running = False
    
    def get_summary(self) -> Dict[str, Any]:
        cutoff = datetime.utcnow() - timedelta(days=self.WINDOW_DAYS)
        recent = [f for f in self._feedback if f.timestamp >= cutoff]
        return {"total_feedback": len(recent), "by_type": {t.value: sum(1 for f in recent if f.feedback_type == t) for t in FeedbackType}, "thresholds": self._thresholds}


tuner = TunerFeedbackLoop()
