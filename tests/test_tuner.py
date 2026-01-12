"""Test tuner feedback loop."""
import pytest
from datetime import datetime
from hornet.tuner import TunerFeedbackLoop, FeedbackType


class TestTunerFeedbackLoop:
    @pytest.fixture
    def tuner(self):
        return TunerFeedbackLoop()
    
    @pytest.mark.asyncio
    async def test_record_feedback(self, tuner):
        record = await tuner.record_feedback(
            incident_id="inc-123",
            agent_name="hunter",
            feedback_type=FeedbackType.APPROVE,
            confidence=0.85,
            user_id="analyst@example.com",
        )
        assert record is not None
        assert record.agent_name == "hunter"
    
    @pytest.mark.asyncio
    async def test_calculate_metrics_empty(self, tuner):
        metrics = await tuner.calculate_metrics("nonexistent")
        assert metrics.total_findings == 0
    
    @pytest.mark.asyncio
    async def test_calculate_metrics_with_data(self, tuner):
        for i in range(10):
            await tuner.record_feedback("inc", "hunter", FeedbackType.APPROVE, 0.8, "user")
        for i in range(2):
            await tuner.record_feedback("inc", "hunter", FeedbackType.REJECT, 0.6, "user")
        
        metrics = await tuner.calculate_metrics("hunter")
        assert metrics.total_findings == 12
        assert metrics.true_positives == 10
        assert metrics.false_positives == 2
        assert metrics.precision == pytest.approx(0.833, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_calculate_adjustment_insufficient_samples(self, tuner):
        await tuner.record_feedback("inc", "test", FeedbackType.APPROVE, 0.8, "user")
        metrics = await tuner.calculate_metrics("test")
        adj = await tuner.calculate_adjustment("test", metrics)
        assert adj is None  # Not enough samples
    
    def test_get_summary(self, tuner):
        summary = tuner.get_summary()
        assert "total_feedback" in summary
        assert "by_type" in summary
