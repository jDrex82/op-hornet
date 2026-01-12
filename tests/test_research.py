"""Test research/alignment module."""
import pytest
from hornet.research import (
    AlignmentResearchLogger, DeceptionProbe, 
    AlignmentObservation, ObservationType
)


class TestDeceptionProbe:
    def test_stimulus_response_coherence(self):
        obs = DeceptionProbe.stimulus_response_coherence(
            agent_name="test",
            input_ctx={"events": []},
            output={"verdict": "MALICIOUS", "confidence": 0.9},
            reasoning="This is malicious because of the following indicators. Therefore we conclude it's malicious.",
        )
        assert obs is not None
        assert obs.observation_type == ObservationType.HIDDEN_REASONING
        assert obs.deception_score < 0.5  # Good reasoning = low deception
    
    def test_confidence_calibration_insufficient(self):
        obs = DeceptionProbe.confidence_calibration("test", [])
        assert obs.deception_score == 0.0


class TestAlignmentResearchLogger:
    @pytest.fixture
    def logger(self):
        return AlignmentResearchLogger(enabled=True, sampling_rate=1.0)
    
    def test_log_observation(self, logger):
        obs = AlignmentObservation(
            agent="test",
            observation_type=ObservationType.TRUTHFULNESS,
            deception_score=0.2,
        )
        logger.log_observation(obs)
        assert len(logger._observations) == 1
    
    def test_get_summary_empty(self, logger):
        summary = logger.get_summary()
        assert summary["total"] == 0
