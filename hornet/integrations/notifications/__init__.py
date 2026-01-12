"""
HORNET Notification Connectors
Send alerts and escalations to humans.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class NotificationPayload:
    incident_id: str
    severity: str
    summary: str
    details: Dict[str, Any]
    dashboard_url: str
    actions_required: bool = False


class NotificationConnector(ABC):
    @abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass


class SlackConnector(NotificationConnector):
    """Slack notification connector."""
    
    def __init__(self, bot_token: str, default_channel: str = "#security-alerts"):
        self.bot_token = bot_token
        self.default_channel = default_channel
        self.client = httpx.AsyncClient()
    
    async def send(self, payload: NotificationPayload, channel: str = None) -> bool:
        severity_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(payload.severity, "⚪")
        
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"{severity_emoji} {payload.severity} Security Incident"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Summary:* {payload.summary}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Incident ID:*\n{payload.incident_id}"},
                {"type": "mrkdwn", "text": f"*Severity:*\n{payload.severity}"},
            ]},
            {"type": "actions", "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "View in Dashboard"}, "url": payload.dashboard_url, "style": "primary"},
            ]},
        ]
        
        if payload.actions_required:
            blocks.insert(2, {"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ *Human action required*"}})
        
        try:
            resp = await self.client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json={"channel": channel or self.default_channel, "blocks": blocks},
            )
            return resp.json().get("ok", False)
        except Exception as e:
            logger.error("slack_send_failed", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        try:
            resp = await self.client.post(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            return resp.json().get("ok", False)
        except:
            return False


class PagerDutyConnector(NotificationConnector):
    """PagerDuty notification connector."""
    
    def __init__(self, integration_key: str):
        self.integration_key = integration_key
        self.client = httpx.AsyncClient()
    
    async def send(self, payload: NotificationPayload) -> bool:
        severity_map = {"CRITICAL": "critical", "HIGH": "error", "MEDIUM": "warning", "LOW": "info"}
        
        event = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "dedup_key": payload.incident_id,
            "payload": {
                "summary": payload.summary,
                "severity": severity_map.get(payload.severity, "info"),
                "source": "HORNET",
                "custom_details": payload.details,
            },
            "links": [{"href": payload.dashboard_url, "text": "View in Dashboard"}],
        }
        
        try:
            resp = await self.client.post("https://events.pagerduty.com/v2/enqueue", json=event)
            return resp.status_code == 202
        except Exception as e:
            logger.error("pagerduty_send_failed", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        return True


class EmailConnector(NotificationConnector):
    """Email notification connector."""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, from_addr: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
    
    async def send(self, payload: NotificationPayload, to_addrs: List[str] = None) -> bool:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{payload.severity}] HORNET Security Alert: {payload.summary}"
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(to_addrs or ["security@example.com"])
        
        html = f"""
        <html><body>
        <h2 style="color: {'red' if payload.severity == 'CRITICAL' else 'orange'};">{payload.severity} Security Incident</h2>
        <p><strong>Summary:</strong> {payload.summary}</p>
        <p><strong>Incident ID:</strong> {payload.incident_id}</p>
        <p><a href="{payload.dashboard_url}">View in Dashboard</a></p>
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, to_addrs or ["security@example.com"], msg.as_string())
            return True
        except Exception as e:
            logger.error("email_send_failed", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        return True


class WebhookConnector(NotificationConnector):
    """Generic webhook connector."""
    
    def __init__(self, url: str, secret: str = None, headers: Dict[str, str] = None):
        self.url = url
        self.secret = secret
        self.headers = headers or {}
        self.client = httpx.AsyncClient()
    
    async def send(self, payload: NotificationPayload) -> bool:
        import hmac
        import hashlib
        import json
        
        body = {
            "event_type": "security_incident",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "incident_id": payload.incident_id,
            "severity": payload.severity,
            "summary": payload.summary,
            "dashboard_url": payload.dashboard_url,
            "details": payload.details,
        }
        
        headers = dict(self.headers)
        if self.secret:
            sig = hmac.new(self.secret.encode(), json.dumps(body).encode(), hashlib.sha256).hexdigest()
            headers["X-HORNET-Signature"] = f"sha256={sig}"
        
        try:
            resp = await self.client.post(self.url, json=body, headers=headers)
            return resp.status_code < 300
        except Exception as e:
            logger.error("webhook_send_failed", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        return True


CONNECTORS = {
    "slack": SlackConnector,
    "pagerduty": PagerDutyConnector,
    "email": EmailConnector,
    "webhook": WebhookConnector,
}
