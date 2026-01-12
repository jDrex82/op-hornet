#!/usr/bin/env python3
"""HORNET Synthetic Event Generator"""
import argparse
import asyncio
import random
import httpx
from datetime import datetime
from uuid import uuid4

SCENARIOS = {
    "brute_force": {"events": [{"type": "auth.login_failure", "sev": "LOW", "count": 50}, {"type": "auth.login_failure", "sev": "MEDIUM", "count": 20}]},
    "ransomware": {"events": [{"type": "endpoint.malware_detected", "sev": "HIGH", "count": 1}, {"type": "endpoint.ransomware_behavior", "sev": "CRITICAL", "count": 3}]},
    "phishing": {"events": [{"type": "email.phishing_detected", "sev": "MEDIUM", "count": 1}]},
    "exfil": {"events": [{"type": "data.mass_download", "sev": "MEDIUM", "count": 3}, {"type": "network.data_exfil", "sev": "HIGH", "count": 1}]},
    "c2_beacon": {"events": [{"type": "network.c2_beacon", "sev": "HIGH", "count": 5}]},
}

def gen_ip(): return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
def gen_user(): return f"user_{random.randint(1,999)}"
def gen_host(): return f"host-{random.randint(1,100)}.corp.local"

def gen_event(etype, sev, ctx):
    return {
        "id": str(uuid4()), "timestamp": datetime.utcnow().isoformat(), "source": "synth",
        "source_type": "synthetic", "event_type": etype, "severity": sev,
        "entities": [{"type": "ip", "value": ctx["ip"]}, {"type": "user", "value": ctx["user"]}],
        "raw_payload": {"source_ip": ctx["ip"], "user": ctx["user"], "host": ctx["host"]},
    }

async def run(scenario, url, verbose):
    if scenario not in SCENARIOS:
        print(f"Unknown: {scenario}. Available: {list(SCENARIOS.keys())}")
        return
    ctx = {"ip": gen_ip(), "user": gen_user(), "host": gen_host()}
    print(f"Running {scenario}...")
    async with httpx.AsyncClient() as c:
        for e in SCENARIOS[scenario]["events"]:
            for _ in range(e.get("count", 1)):
                ev = gen_event(e["type"], e["sev"], ctx)
                if verbose: print(f"  {e['type']}")
                try: await c.post(f"{url}/api/v1/events", json=ev)
                except: pass
                await asyncio.sleep(0.05)
    print("Done.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", "-s", default="brute_force")
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("-v", action="store_true")
    a = p.parse_args()
    asyncio.run(run(a.scenario, a.url, a.v))
