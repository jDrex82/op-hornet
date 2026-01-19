"""
HORNET Edge Agent - Test Client
Connects to HORNET cloud and sends sample logs.
"""
import asyncio
import json
import websockets
from datetime import datetime
from uuid import uuid4

CLOUD_URL = "ws://localhost:8000/api/v1/edge/connect?api_key=hnt_testlab_2026"
AGENT_VERSION = "0.1.0"
HOSTNAME = "test-edge-agent"

async def main():
    print(f"[*] Connecting to HORNET Cloud...")
    
    async with websockets.connect(CLOUD_URL) as ws:
        # Step 1: Register
        await ws.send(json.dumps({
            "type": "register",
            "hostname": HOSTNAME,
            "version": AGENT_VERSION,
            "capabilities": ["syslog", "winevent", "paloalto"],
        }))
        
        response = await ws.recv()
        data = json.loads(response)
        print(f"[+] Registered: {data}")
        agent_id = data.get("agent_id")
        
        # Step 2: Send a test log batch
        test_events = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "paloalto-fw01",
                "source_type": "firewall",
                "event_type": "traffic.deny",
                "severity": "MEDIUM",
                "raw": {"src_ip": "10.0.0.50", "dst_ip": "8.8.8.8", "dst_port": 53, "action": "deny"},
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "dc01.hospital.local",
                "source_type": "windows",
                "event_type": "auth.failure",
                "severity": "HIGH",
                "raw": {"EventID": 4625, "TargetUserName": "admin", "IpAddress": "192.168.1.100"},
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "syslog-collector",
                "source_type": "syslog",
                "event_type": "system.alert",
                "severity": "LOW",
                "raw": {"facility": "auth", "message": "Failed password for root from 10.0.0.99"},
            },
        ]
        
        batch_id = str(uuid4())
        await ws.send(json.dumps({
            "type": "log_batch",
            "batch_id": batch_id,
            "events": test_events,
        }))
        
        response = await ws.recv()
        data = json.loads(response)
        print(f"[+] Batch acknowledged: {data}")
        
        # Step 3: Send heartbeat
        await ws.send(json.dumps({"type": "heartbeat"}))
        response = await ws.recv()
        data = json.loads(response)
        print(f"[+] Heartbeat response: {data}")
        
        # Step 4: Keep alive and listen for actions
        print(f"[*] Agent {agent_id} listening for actions (Ctrl+C to exit)...")
        
        while True:
            try:
                # Send heartbeat every 30 seconds
                await asyncio.sleep(30)
                await ws.send(json.dumps({"type": "heartbeat"}))
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                
                if data.get("type") == "action_request":
                    print(f"[!] ACTION RECEIVED: {data}")
                    # Simulate execution
                    action = data.get("action", {})
                    await ws.send(json.dumps({
                        "type": "action_result",
                        "action_id": action.get("action_id"),
                        "success": True,
                        "message": f"Executed {action.get('action_type')} on {action.get('target')}",
                    }))
                else:
                    print(f"[.] Heartbeat OK: {data.get('server_time')}")
                    
            except asyncio.TimeoutError:
                continue
            except KeyboardInterrupt:
                print("\n[*] Shutting down...")
                break

if __name__ == "__main__":
    asyncio.run(main())
