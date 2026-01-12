"""Test baseline engine."""
import pytest
from hornet.baseline import BaselineEngine, BaselineMetric, AnomalyLevel


@pytest.fixture
def engine():
    return BaselineEngine()


def test_calculate_zscore(engine):
    z = engine.calculate_z_score(100, 50, 10)
    assert z == 5.0
    
    z = engine.calculate_z_score(50, 50, 10)
    assert z == 0.0


def test_get_anomaly_level(engine):
    assert engine.get_anomaly_level(0.5) == AnomalyLevel.NORMAL
    assert engine.get_anomaly_level(2.5) == AnomalyLevel.SUSPICIOUS
    assert engine.get_anomaly_level(4.0) == AnomalyLevel.ANOMALOUS


def test_calculate_metric(engine):
    values = [10, 20, 30, 40, 50]
    metric = engine.calculate_metric(values, "test_metric")
    
    assert metric.name == "test_metric"
    assert metric.mean == 30.0
    assert metric.min_value == 10
    assert metric.max_value == 50
    assert metric.sample_count == 5


def test_check_deviation_normal(engine):
    metric = BaselineMetric(
        name="test",
        mean=50.0,
        std=10.0,
        min_value=20,
        max_value=80,
        sample_count=100,
    )
    
    result = engine.check_deviation(metric, 55)
    
    assert result.level == AnomalyLevel.NORMAL
    assert result.z_score == 0.5


def test_check_deviation_anomalous(engine):
    metric = BaselineMetric(
        name="test",
        mean=50.0,
        std=10.0,
        min_value=20,
        max_value=80,
        sample_count=100,
    )
    
    result = engine.check_deviation(metric, 90)  # 4 std deviations
    
    assert result.level == AnomalyLevel.ANOMALOUS
    assert result.z_score == 4.0
