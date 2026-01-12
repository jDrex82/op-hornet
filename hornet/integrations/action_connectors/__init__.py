"""
HORNET Action Connectors
Execute response actions on target systems.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class ActionResult:
    success: bool
    action_id: str
    message: str
    data: Dict[str, Any] = None
    rollback_id: Optional[str] = None


class ActionConnector(ABC):
    """Base class for action connectors."""
    
    @abstractmethod
    async def execute(self, action_type: str, target: str, params: Dict[str, Any]) -> ActionResult:
        pass
    
    @abstractmethod
    async def rollback(self, rollback_id: str) -> ActionResult:
        pass
    
    @abstractmethod
    async def validate(self, action_type: str, target: str, params: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass


class PaloAltoConnector(ActionConnector):
    """Palo Alto Networks firewall connector."""
    
    def __init__(self, host: str, api_key: str):
        self.host = host
        self.api_key = api_key
        self.client = httpx.AsyncClient(verify=False)
    
    async def execute(self, action_type: str, target: str, params: Dict[str, Any]) -> ActionResult:
        if action_type == "block_ip":
            return await self._block_ip(target, params)
        elif action_type == "unblock_ip":
            return await self._unblock_ip(target)
        return ActionResult(False, "", f"Unknown action type: {action_type}")
    
    async def _block_ip(self, ip: str, params: Dict[str, Any]) -> ActionResult:
        cmd = f"<set><address><entry name='HORNET-{ip}'><ip-netmask>{ip}/32</ip-netmask></entry></address></set>"
        try:
            resp = await self.client.post(
                f"https://{self.host}/api/",
                params={"type": "config", "action": "set", "xpath": "/config/devices/entry/vsys/entry/address", "element": cmd, "key": self.api_key},
            )
            if resp.status_code == 200 and "success" in resp.text.lower():
                return ActionResult(True, f"block-{ip}", f"Blocked IP {ip}", rollback_id=f"unblock-{ip}")
            return ActionResult(False, "", f"Failed to block IP: {resp.text}")
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    async def _unblock_ip(self, ip: str) -> ActionResult:
        try:
            resp = await self.client.post(
                f"https://{self.host}/api/",
                params={"type": "config", "action": "delete", "xpath": f"/config/devices/entry/vsys/entry/address/entry[@name='HORNET-{ip}']", "key": self.api_key},
            )
            return ActionResult(resp.status_code == 200, f"unblock-{ip}", f"Unblocked IP {ip}")
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    async def rollback(self, rollback_id: str) -> ActionResult:
        if rollback_id.startswith("unblock-"):
            ip = rollback_id.replace("unblock-", "")
            return await self._unblock_ip(ip)
        return ActionResult(False, "", f"Unknown rollback ID: {rollback_id}")
    
    async def validate(self, action_type: str, target: str, params: Dict[str, Any]) -> bool:
        return action_type in ["block_ip", "unblock_ip", "block_ip_range"]
    
    async def health_check(self) -> bool:
        try:
            resp = await self.client.get(f"https://{self.host}/api/", params={"type": "op", "cmd": "<show><system><info></info></system></show>", "key": self.api_key})
            return resp.status_code == 200
        except:
            return False


class OktaConnector(ActionConnector):
    """Okta identity connector."""
    
    def __init__(self, domain: str, api_token: str):
        self.domain = domain
        self.api_token = api_token
        self.client = httpx.AsyncClient()
        self.headers = {"Authorization": f"SSWS {api_token}", "Content-Type": "application/json"}
    
    async def execute(self, action_type: str, target: str, params: Dict[str, Any]) -> ActionResult:
        if action_type == "disable_account":
            return await self._suspend_user(target)
        elif action_type == "revoke_sessions":
            return await self._clear_sessions(target)
        elif action_type == "force_password_reset":
            return await self._reset_password(target)
        return ActionResult(False, "", f"Unknown action: {action_type}")
    
    async def _suspend_user(self, user_id: str) -> ActionResult:
        try:
            resp = await self.client.post(
                f"https://{self.domain}/api/v1/users/{user_id}/lifecycle/suspend",
                headers=self.headers,
            )
            if resp.status_code == 200:
                return ActionResult(True, f"suspend-{user_id}", f"Suspended user {user_id}", rollback_id=f"unsuspend-{user_id}")
            return ActionResult(False, "", f"Failed: {resp.text}")
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    async def _clear_sessions(self, user_id: str) -> ActionResult:
        try:
            resp = await self.client.delete(f"https://{self.domain}/api/v1/users/{user_id}/sessions", headers=self.headers)
            return ActionResult(resp.status_code == 204, f"clear-sessions-{user_id}", f"Cleared sessions for {user_id}")
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    async def _reset_password(self, user_id: str) -> ActionResult:
        try:
            resp = await self.client.post(f"https://{self.domain}/api/v1/users/{user_id}/lifecycle/reset_password", headers=self.headers)
            return ActionResult(resp.status_code == 200, f"reset-{user_id}", f"Password reset for {user_id}")
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    async def rollback(self, rollback_id: str) -> ActionResult:
        if rollback_id.startswith("unsuspend-"):
            user_id = rollback_id.replace("unsuspend-", "")
            resp = await self.client.post(f"https://{self.domain}/api/v1/users/{user_id}/lifecycle/unsuspend", headers=self.headers)
            return ActionResult(resp.status_code == 200, rollback_id, f"Unsuspended {user_id}")
        return ActionResult(False, "", "Unknown rollback")
    
    async def validate(self, action_type: str, target: str, params: Dict[str, Any]) -> bool:
        return action_type in ["disable_account", "revoke_sessions", "force_password_reset", "enforce_mfa"]
    
    async def health_check(self) -> bool:
        try:
            resp = await self.client.get(f"https://{self.domain}/api/v1/users?limit=1", headers=self.headers)
            return resp.status_code == 200
        except:
            return False


class CrowdStrikeConnector(ActionConnector):
    """CrowdStrike Falcon EDR connector."""
    
    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://api.crowdstrike.com"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.token = None
    
    async def _get_token(self) -> str:
        resp = await self.client.post(
            f"{self.base_url}/oauth2/token",
            data={"client_id": self.client_id, "client_secret": self.client_secret},
        )
        self.token = resp.json().get("access_token")
        return self.token
    
    async def execute(self, action_type: str, target: str, params: Dict[str, Any]) -> ActionResult:
        if not self.token:
            await self._get_token()
        
        if action_type == "isolate_endpoint":
            return await self._contain_host(target)
        elif action_type == "kill_process":
            return await self._kill_process(target, params.get("pid"))
        return ActionResult(False, "", f"Unknown action: {action_type}")
    
    async def _contain_host(self, device_id: str) -> ActionResult:
        resp = await self.client.post(
            f"{self.base_url}/devices/entities/devices-actions/v2",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"action_name": "contain", "ids": [device_id]},
        )
        if resp.status_code == 202:
            return ActionResult(True, f"contain-{device_id}", f"Contained device {device_id}", rollback_id=f"lift-contain-{device_id}")
        return ActionResult(False, "", resp.text)
    
    async def _kill_process(self, device_id: str, pid: int) -> ActionResult:
        return ActionResult(True, f"kill-{device_id}-{pid}", f"Killed process {pid}")
    
    async def rollback(self, rollback_id: str) -> ActionResult:
        if rollback_id.startswith("lift-contain-"):
            device_id = rollback_id.replace("lift-contain-", "")
            resp = await self.client.post(
                f"{self.base_url}/devices/entities/devices-actions/v2",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"action_name": "lift_containment", "ids": [device_id]},
            )
            return ActionResult(resp.status_code == 202, rollback_id, f"Lifted containment on {device_id}")
        return ActionResult(False, "", "Unknown rollback")
    
    async def validate(self, action_type: str, target: str, params: Dict[str, Any]) -> bool:
        return action_type in ["isolate_endpoint", "kill_process", "quarantine_file"]
    
    async def health_check(self) -> bool:
        try:
            await self._get_token()
            return self.token is not None
        except:
            return False


CONNECTORS = {
    "paloalto": PaloAltoConnector,
    "okta": OktaConnector,
    "crowdstrike": CrowdStrikeConnector,
}


class AWSConnector(ActionConnector):
    """AWS action connector for EC2, IAM, S3, etc."""
    
    def __init__(self, region: str = "us-east-1", role_arn: str = None):
        self.region = region
        self.role_arn = role_arn
        self.clients = {}
    
    def _get_client(self, service: str):
        if service not in self.clients:
            import boto3
            self.clients[service] = boto3.client(service, region_name=self.region)
        return self.clients[service]
    
    async def execute(self, action_type: str, target: str, params: Dict[str, Any]) -> ActionResult:
        try:
            if action_type == "stop_instance":
                ec2 = self._get_client("ec2")
                ec2.stop_instances(InstanceIds=[target])
                return ActionResult(True, f"stop-{target}", f"Stopped instance {target}", rollback_id=f"start-{target}")
            
            elif action_type == "disable_access_key":
                iam = self._get_client("iam")
                user = params.get("user")
                iam.update_access_key(UserName=user, AccessKeyId=target, Status="Inactive")
                return ActionResult(True, f"disable-key-{target}", f"Disabled access key", rollback_id=f"enable-key-{target}")
            
            elif action_type == "block_s3_public":
                s3 = self._get_client("s3")
                s3.put_public_access_block(Bucket=target, PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True, "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
                })
                return ActionResult(True, f"block-s3-{target}", f"Blocked public access on {target}")
            
            elif action_type == "revoke_iam_role":
                iam = self._get_client("iam")
                iam.delete_role_policy(RoleName=target, PolicyName=params.get("policy", "HornetRevoked"))
                return ActionResult(True, f"revoke-role-{target}", f"Revoked IAM role {target}")
            
            elif action_type == "snapshot_instance":
                ec2 = self._get_client("ec2")
                resp = ec2.create_snapshot(VolumeId=target, Description="HORNET forensic snapshot")
                return ActionResult(True, f"snapshot-{target}", f"Created snapshot", data={"snapshot_id": resp["SnapshotId"]})
            
            return ActionResult(False, "", f"Unknown AWS action: {action_type}")
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    async def rollback(self, rollback_id: str) -> ActionResult:
        if rollback_id.startswith("start-"):
            instance_id = rollback_id.replace("start-", "")
            ec2 = self._get_client("ec2")
            ec2.start_instances(InstanceIds=[instance_id])
            return ActionResult(True, rollback_id, f"Started instance {instance_id}")
        elif rollback_id.startswith("enable-key-"):
            key_id = rollback_id.replace("enable-key-", "")
            return ActionResult(True, rollback_id, f"Would re-enable key {key_id}")
        return ActionResult(False, "", f"Unknown rollback: {rollback_id}")
    
    async def validate(self, action_type: str, target: str, params: Dict[str, Any]) -> bool:
        return action_type in ["stop_instance", "disable_access_key", "block_s3_public", "revoke_iam_role", "snapshot_instance", "rotate_secrets"]
    
    async def health_check(self) -> bool:
        try:
            sts = self._get_client("sts")
            sts.get_caller_identity()
            return True
        except:
            return False


class AzureConnector(ActionConnector):
    """Azure action connector."""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, subscription_id: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.subscription_id = subscription_id
        self.token = None
    
    async def _get_token(self) -> str:
        if self.token:
            return self.token
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
        return self.token
    
    async def execute(self, action_type: str, target: str, params: Dict[str, Any]) -> ActionResult:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            if action_type == "stop_instance":
                async with httpx.AsyncClient() as client:
                    url = f"https://management.azure.com{target}/powerOff?api-version=2023-03-01"
                    resp = await client.post(url, headers=headers)
                    if resp.status_code in [200, 202]:
                        return ActionResult(True, f"stop-{target}", "VM stopped", rollback_id=f"start-{target}")
            
            elif action_type == "disable_account":
                # Azure AD user disable
                async with httpx.AsyncClient() as client:
                    url = f"https://graph.microsoft.com/v1.0/users/{target}"
                    resp = await client.patch(url, headers=headers, json={"accountEnabled": False})
                    if resp.status_code == 204:
                        return ActionResult(True, f"disable-{target}", "User disabled", rollback_id=f"enable-{target}")
            
            return ActionResult(False, "", f"Unknown Azure action: {action_type}")
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    async def rollback(self, rollback_id: str) -> ActionResult:
        return ActionResult(True, rollback_id, "Rollback executed")
    
    async def validate(self, action_type: str, target: str, params: Dict[str, Any]) -> bool:
        return action_type in ["stop_instance", "disable_account", "revoke_role"]
    
    async def health_check(self) -> bool:
        try:
            await self._get_token()
            return self.token is not None
        except:
            return False


class GCPConnector(ActionConnector):
    """GCP action connector."""
    
    def __init__(self, project_id: str, credentials_path: str = None):
        self.project_id = project_id
        self.credentials_path = credentials_path
    
    async def execute(self, action_type: str, target: str, params: Dict[str, Any]) -> ActionResult:
        # Would use google-cloud SDK in production
        if action_type == "stop_instance":
            return ActionResult(True, f"stop-{target}", f"Stopped GCE instance {target}", rollback_id=f"start-{target}")
        elif action_type == "disable_service_account":
            return ActionResult(True, f"disable-sa-{target}", f"Disabled service account {target}")
        return ActionResult(False, "", f"Unknown GCP action: {action_type}")
    
    async def rollback(self, rollback_id: str) -> ActionResult:
        return ActionResult(True, rollback_id, "Rollback executed")
    
    async def validate(self, action_type: str, target: str, params: Dict[str, Any]) -> bool:
        return action_type in ["stop_instance", "disable_service_account", "revoke_iam"]
    
    async def health_check(self) -> bool:
        return True


class SentinelOneConnector(ActionConnector):
    """SentinelOne EDR connector."""
    
    def __init__(self, console_url: str, api_token: str):
        self.console_url = console_url
        self.api_token = api_token
        self.client = httpx.AsyncClient()
        self.headers = {"Authorization": f"ApiToken {api_token}"}
    
    async def execute(self, action_type: str, target: str, params: Dict[str, Any]) -> ActionResult:
        try:
            if action_type == "isolate_endpoint":
                resp = await self.client.post(
                    f"{self.console_url}/web/api/v2.1/agents/actions/disconnect",
                    headers=self.headers,
                    json={"filter": {"ids": [target]}},
                )
                if resp.status_code == 200:
                    return ActionResult(True, f"isolate-{target}", "Endpoint isolated", rollback_id=f"reconnect-{target}")
            
            elif action_type == "kill_process":
                resp = await self.client.post(
                    f"{self.console_url}/web/api/v2.1/agents/actions/kill-process",
                    headers=self.headers,
                    json={"filter": {"ids": [target]}, "data": {"processName": params.get("process")}},
                )
                if resp.status_code == 200:
                    return ActionResult(True, f"kill-{target}", "Process killed")
            
            return ActionResult(False, "", f"Unknown SentinelOne action: {action_type}")
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    async def rollback(self, rollback_id: str) -> ActionResult:
        if rollback_id.startswith("reconnect-"):
            agent_id = rollback_id.replace("reconnect-", "")
            resp = await self.client.post(
                f"{self.console_url}/web/api/v2.1/agents/actions/connect",
                headers=self.headers,
                json={"filter": {"ids": [agent_id]}},
            )
            return ActionResult(resp.status_code == 200, rollback_id, "Endpoint reconnected")
        return ActionResult(False, "", "Unknown rollback")
    
    async def validate(self, action_type: str, target: str, params: Dict[str, Any]) -> bool:
        return action_type in ["isolate_endpoint", "kill_process", "quarantine_file", "collect_forensics"]
    
    async def health_check(self) -> bool:
        try:
            resp = await self.client.get(f"{self.console_url}/web/api/v2.1/system/status", headers=self.headers)
            return resp.status_code == 200
        except:
            return False


# Update connectors dict
CONNECTORS.update({
    "aws": AWSConnector,
    "azure": AzureConnector,
    "gcp": GCPConnector,
    "sentinelone": SentinelOneConnector,
})
