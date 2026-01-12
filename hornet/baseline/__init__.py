"""
HORNET Baseline Engine
Behavioral baselines with z-score anomaly detection.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import math
import statistics
import structlog

from hornet.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AnomalyLevel(str, Enum):
    NORMAL = "NORMAL"           # z < 2.0
    SUSPICIOUS = "SUSPICIOUS"   # 2.0 <= z < 3.0
    ANOMALOUS = "ANOMALOUS"     # z >= 3.0


@dataclass
class BaselineMetric:
    """Single metric in a baseline."""
    name: str
    mean: float
    std: float
    min_value: float
    max_value: float
    percentiles: Dict[int, float] = field(default_factory=dict)  # p50, p90, p95, p99
    sample_count: int = 0


@dataclass
class UserBaseline:
    """Behavioral baseline for a user."""
    user_id: str
    tenant_id: str
    calculated_at: datetime
    valid_until: datetime
    data_points: int
    
    # Login patterns
    login_hours: BaselineMetric = None  # Hour of day (0-23)
    login_days: BaselineMetric = None   # Day of week (0-6)
    login_locations: List[str] = field(default_factory=list)  # Common IPs/geos
    working_hours: Tuple[int, int] = (8, 18)  # Start, end hour
    
    # Data access patterns
    data_volume_daily: BaselineMetric = None  # Bytes accessed per day
    files_accessed_daily: BaselineMetric = None
    sensitive_access_daily: BaselineMetric = None
    
    # Session patterns
    session_duration: BaselineMetric = None  # Minutes
    sessions_per_day: BaselineMetric = None
    
    # Peer group (for comparison)
    peer_group: str = None  # e.g., "engineering", "finance"
    peer_baseline: Optional["UserBaseline"] = None


@dataclass
class HostBaseline:
    """Behavioral baseline for a host/asset."""
    host_id: str
    tenant_id: str
    calculated_at: datetime
    valid_until: datetime
    
    # Network patterns
    bytes_out_hourly: BaselineMetric = None
    bytes_in_hourly: BaselineMetric = None
    connections_hourly: BaselineMetric = None
    unique_destinations_daily: BaselineMetric = None
    
    # Process patterns
    process_count: BaselineMetric = None
    cpu_usage: BaselineMetric = None
    memory_usage: BaselineMetric = None
    
    # Ports and protocols
    common_ports: List[int] = field(default_factory=list)
    common_protocols: List[str] = field(default_factory=list)
    
    # Services
    expected_services: List[str] = field(default_factory=list)


@dataclass
class NetworkBaseline:
    """Behavioral baseline for a network segment."""
    segment_id: str
    tenant_id: str
    calculated_at: datetime
    valid_until: datetime
    
    # Traffic patterns
    total_bytes_hourly: BaselineMetric = None
    connection_count_hourly: BaselineMetric = None
    unique_sources_hourly: BaselineMetric = None
    unique_destinations_hourly: BaselineMetric = None
    
    # Protocol distribution
    protocol_distribution: Dict[str, float] = field(default_factory=dict)
    
    # DNS patterns
    dns_queries_hourly: BaselineMetric = None
    unique_domains_hourly: BaselineMetric = None


@dataclass
class DeviationResult:
    """Result of checking a value against baseline."""
    metric_name: str
    observed_value: float
    expected_mean: float
    expected_std: float
    z_score: float
    level: AnomalyLevel
    percentile: float  # Where this value falls in historical distribution
    message: str


class BaselineEngine:
    """
    Engine for calculating and checking baselines.
    """
    
    # Configuration
    USER_BASELINE_WINDOW_DAYS = 30
    USER_BASELINE_MIN_POINTS = 50
    HOST_BASELINE_WINDOW_DAYS = 14
    HOST_BASELINE_MIN_POINTS = 100
    NETWORK_BASELINE_WINDOW_HOURS = 168  # 7 days
    
    Z_THRESHOLD_SUSPICIOUS = 2.0
    Z_THRESHOLD_ANOMALOUS = 3.0
    
    def __init__(self, db_session=None):
        self.db = db_session
    
    def calculate_z_score(self, value: float, mean: float, std: float) -> float:
        """Calculate z-score for anomaly detection."""
        if std == 0:
            return 0.0 if value == mean else float('inf') if value > mean else float('-inf')
        return (value - mean) / std
    
    def get_anomaly_level(self, z_score: float) -> AnomalyLevel:
        """Determine anomaly level from z-score."""
        abs_z = abs(z_score)
        if abs_z >= self.Z_THRESHOLD_ANOMALOUS:
            return AnomalyLevel.ANOMALOUS
        elif abs_z >= self.Z_THRESHOLD_SUSPICIOUS:
            return AnomalyLevel.SUSPICIOUS
        return AnomalyLevel.NORMAL
    
    def calculate_metric(self, values: List[float], name: str) -> BaselineMetric:
        """Calculate a baseline metric from historical values."""
        if not values:
            return BaselineMetric(name=name, mean=0, std=0, min_value=0, max_value=0, sample_count=0)
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return BaselineMetric(
            name=name,
            mean=statistics.mean(values),
            std=statistics.stdev(values) if n > 1 else 0,
            min_value=min(values),
            max_value=max(values),
            percentiles={
                50: sorted_values[int(n * 0.50)],
                90: sorted_values[int(n * 0.90)],
                95: sorted_values[int(n * 0.95)],
                99: sorted_values[min(int(n * 0.99), n - 1)],
            },
            sample_count=n,
        )
    
    def check_deviation(
        self,
        metric: BaselineMetric,
        observed_value: float,
    ) -> DeviationResult:
        """Check if an observed value deviates from baseline."""
        if metric is None or metric.sample_count < 10:
            return DeviationResult(
                metric_name=metric.name if metric else "unknown",
                observed_value=observed_value,
                expected_mean=0,
                expected_std=0,
                z_score=0,
                level=AnomalyLevel.NORMAL,
                percentile=50,
                message="Insufficient baseline data",
            )
        
        z_score = self.calculate_z_score(observed_value, metric.mean, metric.std)
        level = self.get_anomaly_level(z_score)
        
        # Calculate approximate percentile
        if metric.std > 0:
            # Using normal distribution approximation
            from math import erf
            percentile = 50 * (1 + erf(z_score / math.sqrt(2)))
        else:
            percentile = 50 if observed_value == metric.mean else (100 if observed_value > metric.mean else 0)
        
        message = self._generate_deviation_message(metric, observed_value, z_score, level)
        
        return DeviationResult(
            metric_name=metric.name,
            observed_value=observed_value,
            expected_mean=metric.mean,
            expected_std=metric.std,
            z_score=z_score,
            level=level,
            percentile=percentile,
            message=message,
        )
    
    def _generate_deviation_message(
        self,
        metric: BaselineMetric,
        observed: float,
        z_score: float,
        level: AnomalyLevel,
    ) -> str:
        """Generate human-readable deviation message."""
        direction = "above" if observed > metric.mean else "below"
        
        if level == AnomalyLevel.NORMAL:
            return f"{metric.name} ({observed:.2f}) is within normal range"
        elif level == AnomalyLevel.SUSPICIOUS:
            return f"{metric.name} ({observed:.2f}) is {abs(z_score):.1f}σ {direction} baseline ({metric.mean:.2f})"
        else:  # ANOMALOUS
            return f"ANOMALY: {metric.name} ({observed:.2f}) is {abs(z_score):.1f}σ {direction} baseline ({metric.mean:.2f})"
    
    async def check_user_behavior(
        self,
        user_id: str,
        tenant_id: str,
        behavior: Dict[str, Any],
    ) -> List[DeviationResult]:
        """Check user behavior against baseline."""
        # Load baseline (would come from database)
        baseline = await self._load_user_baseline(user_id, tenant_id)
        if not baseline:
            logger.warning("no_baseline_found", user_id=user_id)
            return []
        
        results = []
        
        # Check login hour
        if 'login_hour' in behavior and baseline.login_hours:
            results.append(self.check_deviation(baseline.login_hours, behavior['login_hour']))
        
        # Check data volume
        if 'data_volume' in behavior and baseline.data_volume_daily:
            results.append(self.check_deviation(baseline.data_volume_daily, behavior['data_volume']))
        
        # Check session duration
        if 'session_duration' in behavior and baseline.session_duration:
            results.append(self.check_deviation(baseline.session_duration, behavior['session_duration']))
        
        # Check location (not z-score, but presence check)
        if 'source_ip' in behavior and baseline.login_locations:
            if behavior['source_ip'] not in baseline.login_locations:
                results.append(DeviationResult(
                    metric_name="login_location",
                    observed_value=0,
                    expected_mean=0,
                    expected_std=0,
                    z_score=3.0,  # Treat as anomalous
                    level=AnomalyLevel.ANOMALOUS,
                    percentile=0,
                    message=f"Login from unknown location: {behavior['source_ip']}",
                ))
        
        return results
    
    async def check_host_behavior(
        self,
        host_id: str,
        tenant_id: str,
        behavior: Dict[str, Any],
    ) -> List[DeviationResult]:
        """Check host behavior against baseline."""
        baseline = await self._load_host_baseline(host_id, tenant_id)
        if not baseline:
            return []
        
        results = []
        
        if 'bytes_out' in behavior and baseline.bytes_out_hourly:
            results.append(self.check_deviation(baseline.bytes_out_hourly, behavior['bytes_out']))
        
        if 'connections' in behavior and baseline.connections_hourly:
            results.append(self.check_deviation(baseline.connections_hourly, behavior['connections']))
        
        if 'unique_destinations' in behavior and baseline.unique_destinations_daily:
            results.append(self.check_deviation(baseline.unique_destinations_daily, behavior['unique_destinations']))
        
        # Check for unexpected ports
        if 'ports' in behavior and baseline.common_ports:
            unexpected = set(behavior['ports']) - set(baseline.common_ports)
            if unexpected:
                results.append(DeviationResult(
                    metric_name="unexpected_ports",
                    observed_value=len(unexpected),
                    expected_mean=0,
                    expected_std=0,
                    z_score=3.0,
                    level=AnomalyLevel.ANOMALOUS,
                    percentile=0,
                    message=f"Unexpected ports detected: {unexpected}",
                ))
        
        return results
    
    async def check_peer_comparison(
        self,
        user_id: str,
        tenant_id: str,
        metric_name: str,
        value: float,
    ) -> Optional[DeviationResult]:
        """Compare user behavior against peer group baseline."""
        baseline = await self._load_user_baseline(user_id, tenant_id)
        if not baseline or not baseline.peer_baseline:
            return None
        
        peer_metric = getattr(baseline.peer_baseline, metric_name, None)
        if not peer_metric:
            return None
        
        return self.check_deviation(peer_metric, value)
    
    async def calculate_user_baseline(
        self,
        user_id: str,
        tenant_id: str,
        historical_events: List[Dict[str, Any]],
    ) -> UserBaseline:
        """Calculate baseline from historical events."""
        if len(historical_events) < self.USER_BASELINE_MIN_POINTS:
            logger.warning("insufficient_data_for_baseline", user_id=user_id, count=len(historical_events))
        
        # Extract metrics from events
        login_hours = []
        data_volumes = []
        session_durations = []
        locations = set()
        
        for event in historical_events:
            ts = event.get('timestamp')
            if ts:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                login_hours.append(ts.hour)
            
            if 'data_volume' in event:
                data_volumes.append(event['data_volume'])
            
            if 'session_duration' in event:
                session_durations.append(event['session_duration'])
            
            if 'source_ip' in event:
                locations.add(event['source_ip'])
        
        now = datetime.utcnow()
        
        return UserBaseline(
            user_id=user_id,
            tenant_id=tenant_id,
            calculated_at=now,
            valid_until=now + timedelta(days=7),
            data_points=len(historical_events),
            login_hours=self.calculate_metric(login_hours, "login_hours") if login_hours else None,
            data_volume_daily=self.calculate_metric(data_volumes, "data_volume_daily") if data_volumes else None,
            session_duration=self.calculate_metric(session_durations, "session_duration") if session_durations else None,
            login_locations=list(locations)[:20],  # Top 20 locations
        )
    
    async def _load_user_baseline(self, user_id: str, tenant_id: str) -> Optional[UserBaseline]:
        """Load user baseline from database."""
        # Would load from database in production
        return None
    
    async def _load_host_baseline(self, host_id: str, tenant_id: str) -> Optional[HostBaseline]:
        """Load host baseline from database."""
        return None


# Global engine instance
baseline_engine = BaselineEngine()
