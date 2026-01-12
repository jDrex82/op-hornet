"""
HORNET Log Source Connectors
Connectors for ingesting logs from various sources.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, AsyncIterator
from datetime import datetime
import httpx
import structlog

logger = structlog.get_logger()


class LogSourceConnector(ABC):
    """Base class for log source connectors."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to log source."""
        pass
    
    @abstractmethod
    async def poll(self) -> AsyncIterator[Dict[str, Any]]:
        """Poll for new events."""
        pass
    
    @abstractmethod
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event to standard schema."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check connector health."""
        pass


class CloudflareConnector(LogSourceConnector):
    """Cloudflare Logpull API connector."""
    
    def __init__(self, zone_id: str, api_token: str):
        self.zone_id = zone_id
        self.api_token = api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/logs"
        self.client = httpx.AsyncClient()
    
    async def connect(self) -> bool:
        try:
            resp = await self.client.get(
                f"{self.base_url}/received",
                headers={"Authorization": f"Bearer {self.api_token}"},
                params={"start": "2024-01-01T00:00:00Z", "end": "2024-01-01T00:01:00Z"},
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("cloudflare_connect_failed", error=str(e))
            return False
    
    async def poll(self) -> AsyncIterator[Dict[str, Any]]:
        end = datetime.utcnow()
        start = end.replace(second=0, microsecond=0)
        
        resp = await self.client.get(
            f"{self.base_url}/received",
            headers={"Authorization": f"Bearer {self.api_token}"},
            params={"start": start.isoformat() + "Z", "end": end.isoformat() + "Z"},
        )
        
        if resp.status_code == 200:
            for line in resp.text.strip().split("\n"):
                if line:
                    import json
                    yield json.loads(line)
    
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": raw_event.get("EdgeStartTimestamp"),
            "source": "cloudflare",
            "source_type": "waf",
            "event_type": f"network.{raw_event.get('EdgeResponseStatus', 'unknown')}",
            "severity": "MEDIUM" if raw_event.get("WAFAction") == "block" else "LOW",
            "entities": [
                {"type": "ip", "value": raw_event.get("ClientIP")},
                {"type": "domain", "value": raw_event.get("ClientRequestHost")},
            ],
            "raw_payload": raw_event,
        }
    
    async def health_check(self) -> bool:
        return await self.connect()


class SyslogConnector(LogSourceConnector):
    """Syslog receiver connector (RFC 3164/5424)."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 514):
        self.host = host
        self.port = port
        self.server = None
    
    async def connect(self) -> bool:
        return True
    
    async def poll(self) -> AsyncIterator[Dict[str, Any]]:
        yield {}
    
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": raw_event.get("timestamp", datetime.utcnow().isoformat()),
            "source": raw_event.get("hostname", "unknown"),
            "source_type": "syslog",
            "event_type": f"system.{raw_event.get('facility', 'unknown')}",
            "severity": raw_event.get("severity", "LOW"),
            "entities": [],
            "raw_payload": raw_event,
        }
    
    async def health_check(self) -> bool:
        return True


CONNECTORS = {
    "cloudflare": CloudflareConnector,
    "syslog": SyslogConnector,
}


class AWSCloudTrailConnector(LogSourceConnector):
    """AWS CloudTrail connector."""
    
    def __init__(self, region: str, bucket: str = None, log_group: str = None):
        self.region = region
        self.bucket = bucket
        self.log_group = log_group
        self.client = None
    
    async def connect(self) -> bool:
        try:
            import boto3
            self.client = boto3.client('logs', region_name=self.region)
            return True
        except Exception as e:
            logger.error("aws_connect_failed", error=str(e))
            return False
    
    async def poll(self) -> AsyncIterator[Dict[str, Any]]:
        if not self.client:
            return
        # Would poll CloudWatch Logs or S3 in production
        yield {}
    
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": raw_event.get("eventTime", datetime.utcnow().isoformat()),
            "source": "aws_cloudtrail",
            "source_type": "cloudtrail",
            "event_type": f"cloud.{raw_event.get('eventName', 'unknown')}",
            "severity": self._calculate_severity(raw_event),
            "entities": [
                {"type": "user", "value": raw_event.get("userIdentity", {}).get("userName", "unknown")},
                {"type": "ip", "value": raw_event.get("sourceIPAddress", "unknown")},
            ],
            "raw_payload": raw_event,
        }
    
    def _calculate_severity(self, event: Dict) -> str:
        event_name = event.get("eventName", "").lower()
        if any(x in event_name for x in ["delete", "remove", "terminate"]):
            return "MEDIUM"
        if any(x in event_name for x in ["iam", "security", "policy", "kms"]):
            return "HIGH"
        return "LOW"
    
    async def health_check(self) -> bool:
        return self.client is not None


class AzureActivityConnector(LogSourceConnector):
    """Azure Activity Log connector."""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, subscription_id: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.subscription_id = subscription_id
        self.token = None
    
    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "https://management.azure.com/.default",
                    },
                )
                self.token = resp.json().get("access_token")
                return self.token is not None
        except Exception as e:
            logger.error("azure_connect_failed", error=str(e))
            return False
    
    async def poll(self) -> AsyncIterator[Dict[str, Any]]:
        if not self.token:
            return
        yield {}
    
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": raw_event.get("eventTimestamp", datetime.utcnow().isoformat()),
            "source": "azure_activity",
            "source_type": "azure",
            "event_type": f"cloud.{raw_event.get('operationName', {}).get('value', 'unknown')}",
            "severity": raw_event.get("level", "LOW"),
            "entities": [
                {"type": "user", "value": raw_event.get("caller", "unknown")},
            ],
            "raw_payload": raw_event,
        }
    
    async def health_check(self) -> bool:
        return self.token is not None


class GCPAuditConnector(LogSourceConnector):
    """GCP Cloud Audit Logs connector."""
    
    def __init__(self, project_id: str, credentials_path: str = None):
        self.project_id = project_id
        self.credentials_path = credentials_path
        self.client = None
    
    async def connect(self) -> bool:
        # Would use google-cloud-logging in production
        return True
    
    async def poll(self) -> AsyncIterator[Dict[str, Any]]:
        yield {}
    
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": raw_event.get("timestamp", datetime.utcnow().isoformat()),
            "source": "gcp_audit",
            "source_type": "gcp",
            "event_type": f"cloud.{raw_event.get('protoPayload', {}).get('methodName', 'unknown')}",
            "severity": "MEDIUM",
            "entities": [],
            "raw_payload": raw_event,
        }
    
    async def health_check(self) -> bool:
        return True


class M365AuditConnector(LogSourceConnector):
    """Microsoft 365 Management Activity API connector."""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
    
    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "https://manage.office.com/.default",
                    },
                )
                self.token = resp.json().get("access_token")
                return self.token is not None
        except:
            return False
    
    async def poll(self) -> AsyncIterator[Dict[str, Any]]:
        yield {}
    
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": raw_event.get("CreationTime", datetime.utcnow().isoformat()),
            "source": "m365",
            "source_type": "m365",
            "event_type": f"cloud.{raw_event.get('Operation', 'unknown')}",
            "severity": "LOW",
            "entities": [
                {"type": "user", "value": raw_event.get("UserId", "unknown")},
            ],
            "raw_payload": raw_event,
        }
    
    async def health_check(self) -> bool:
        return self.token is not None


class DefenderConnector(LogSourceConnector):
    """Microsoft Defender for Endpoint connector."""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
    
    async def connect(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "https://api.securitycenter.microsoft.com/.default",
                    },
                )
                self.token = resp.json().get("access_token")
                return self.token is not None
        except:
            return False
    
    async def poll(self) -> AsyncIterator[Dict[str, Any]]:
        if not self.token:
            return
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.securitycenter.microsoft.com/api/alerts",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if resp.status_code == 200:
                for alert in resp.json().get("value", []):
                    yield alert
    
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        severity_map = {"Informational": "LOW", "Low": "LOW", "Medium": "MEDIUM", "High": "HIGH", "Critical": "CRITICAL"}
        return {
            "timestamp": raw_event.get("alertCreationTime", datetime.utcnow().isoformat()),
            "source": "defender",
            "source_type": "edr",
            "event_type": f"endpoint.{raw_event.get('category', 'unknown')}",
            "severity": severity_map.get(raw_event.get("severity"), "MEDIUM"),
            "entities": [
                {"type": "host", "value": raw_event.get("computerDnsName", "unknown")},
            ],
            "raw_payload": raw_event,
        }
    
    async def health_check(self) -> bool:
        return self.token is not None


# Update connectors dict
CONNECTORS.update({
    "aws_cloudtrail": AWSCloudTrailConnector,
    "azure_activity": AzureActivityConnector,
    "gcp_audit": GCPAuditConnector,
    "m365": M365AuditConnector,
    "defender": DefenderConnector,
})
