"""
HORNET CLI
Command-line interface for HORNET operations.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime

import httpx


class HornetCLI:
    """HORNET command-line interface."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key} if api_key else {}
    
    async def health(self):
        """Check system health."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/health")
            return resp.json()
    
    async def list_incidents(self, state: str = None, limit: int = 10):
        """List incidents."""
        params = {"limit": limit}
        if state:
            params["state"] = state
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/incidents", params=params, headers=self.headers)
            return resp.json()
    
    async def get_incident(self, incident_id: str):
        """Get incident details."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/incidents/{incident_id}", headers=self.headers)
            return resp.json()
    
    async def ingest_event(self, event_data: dict):
        """Ingest an event."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/api/v1/events", json=event_data, headers=self.headers)
            return resp.json()
    
    async def list_agents(self):
        """List available agents."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/config/agents", headers=self.headers)
            return resp.json()
    
    async def list_playbooks(self):
        """List available playbooks."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/config/playbooks", headers=self.headers)
            return resp.json()
    
    async def get_thresholds(self):
        """Get detection thresholds."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/config/thresholds", headers=self.headers)
            return resp.json()
    
    async def get_metrics(self):
        """Get Prometheus metrics."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/metrics")
            return resp.text
    
    async def approve_action(self, incident_id: str, action_id: str, approve: bool = True, justification: str = ""):
        """Approve or reject an action."""
        data = {
            "response_type": "APPROVE" if approve else "REJECT",
            "justification": justification,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/api/v1/incidents/{incident_id}/actions/{action_id}/approve", json=data, headers=self.headers)
            return resp.json()


def main():
    parser = argparse.ArgumentParser(description="HORNET CLI")
    parser.add_argument("--url", default="http://localhost:8000", help="HORNET API URL")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--format", choices=["json", "table"], default="json", help="Output format")
    
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Health
    subparsers.add_parser("health", help="Check system health")
    
    # Incidents
    incidents_parser = subparsers.add_parser("incidents", help="List incidents")
    incidents_parser.add_argument("--state", help="Filter by state")
    incidents_parser.add_argument("--limit", type=int, default=10, help="Max results")
    
    # Get incident
    get_parser = subparsers.add_parser("get", help="Get incident details")
    get_parser.add_argument("incident_id", help="Incident ID")
    
    # Ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest event")
    ingest_parser.add_argument("--file", help="JSON file with event data")
    ingest_parser.add_argument("--type", default="test.event", help="Event type")
    ingest_parser.add_argument("--severity", default="MEDIUM", help="Severity")
    
    # Agents
    subparsers.add_parser("agents", help="List agents")
    
    # Playbooks
    subparsers.add_parser("playbooks", help="List playbooks")
    
    # Thresholds
    subparsers.add_parser("thresholds", help="Get thresholds")
    
    # Metrics
    subparsers.add_parser("metrics", help="Get metrics")
    
    # Approve
    approve_parser = subparsers.add_parser("approve", help="Approve action")
    approve_parser.add_argument("incident_id", help="Incident ID")
    approve_parser.add_argument("action_id", help="Action ID")
    approve_parser.add_argument("--reject", action="store_true", help="Reject instead of approve")
    approve_parser.add_argument("--justification", default="", help="Justification")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    cli = HornetCLI(args.url, args.api_key)
    
    async def run():
        if args.command == "health":
            result = await cli.health()
        elif args.command == "incidents":
            result = await cli.list_incidents(args.state, args.limit)
        elif args.command == "get":
            result = await cli.get_incident(args.incident_id)
        elif args.command == "ingest":
            if args.file:
                with open(args.file) as f:
                    event_data = json.load(f)
            else:
                event_data = {
                    "event_type": args.type,
                    "source": "cli",
                    "source_type": "manual",
                    "severity": args.severity,
                    "timestamp": datetime.utcnow().isoformat(),
                    "entities": [],
                    "raw_payload": {},
                }
            result = await cli.ingest_event(event_data)
        elif args.command == "agents":
            result = await cli.list_agents()
        elif args.command == "playbooks":
            result = await cli.list_playbooks()
        elif args.command == "thresholds":
            result = await cli.get_thresholds()
        elif args.command == "metrics":
            result = await cli.get_metrics()
            print(result)
            return
        elif args.command == "approve":
            result = await cli.approve_action(args.incident_id, args.action_id, not args.reject, args.justification)
        else:
            parser.print_help()
            return
        
        if args.format == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            # Simple table format
            if isinstance(result, dict):
                for k, v in result.items():
                    print(f"{k}: {v}")
    
    asyncio.run(run())


if __name__ == "__main__":
    main()
