"""Test integration connectors."""
import pytest
from hornet.integrations.log_sources import CONNECTORS as LOG_CONNECTORS
from hornet.integrations.action_connectors import CONNECTORS as ACTION_CONNECTORS
from hornet.integrations.notifications import NOTIFICATION_CHANNELS


class TestLogSourceConnectors:
    def test_has_cloudflare(self):
        assert "cloudflare" in LOG_CONNECTORS
    
    def test_has_aws(self):
        assert "aws_cloudtrail" in LOG_CONNECTORS
    
    def test_has_azure(self):
        assert "azure_activity" in LOG_CONNECTORS
    
    def test_has_syslog(self):
        assert "syslog" in LOG_CONNECTORS


class TestActionConnectors:
    def test_has_paloalto(self):
        assert "paloalto" in ACTION_CONNECTORS
    
    def test_has_okta(self):
        assert "okta" in ACTION_CONNECTORS
    
    def test_has_crowdstrike(self):
        assert "crowdstrike" in ACTION_CONNECTORS
    
    def test_has_aws(self):
        assert "aws" in ACTION_CONNECTORS
    
    def test_has_azure(self):
        assert "azure" in ACTION_CONNECTORS


class TestNotificationChannels:
    def test_has_slack(self):
        assert "slack" in NOTIFICATION_CHANNELS
    
    def test_has_pagerduty(self):
        assert "pagerduty" in NOTIFICATION_CHANNELS
    
    def test_has_email(self):
        assert "email" in NOTIFICATION_CHANNELS
