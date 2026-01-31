#!/usr/bin/env python3
"""Test correct Data API endpoint."""

import asyncio
import httpx

TRADER = "0xc257ea7e3a81ca8e16df8935d44d513959fa358e"

async def test():
    print("=" * 60)
    print("FINDING CORRECT ENDPOINT")
    print("=" * 60)
    
    base = "https://data-api.polymarket.com"
    
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        # Try activity endpoint from docs
        print("\n1. /activity (no prefix):")
        resp = await client.get(f"{base}/activity?user={TRADER}")
        print(f"   Status: {resp.status_code}")
        print(f"   Type: {resp.headers.get('content-type', 'unknown')[:30]}")
        if resp.status_code == 200 and "application/json" in resp.headers.get("content-type", ""):
            data = resp.json()
            print(f"   ✓ JSON with {len(data) if isinstance(data, list) else 'unknown'} items")
            if isinstance(data, list) and len(data) > 0:
                print(f"   Sample: {data[0] if len(data) > 0 else 'empty'}")
        else:
            print(f"   Preview: {resp.text[:200]}")
        
        # Try trades endpoint
        print("\n2. /trades:")
        resp = await client.get(f"{base}/trades?user={TRADER}")
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200 and "application/json" in resp.headers.get("content-type", ""):
            data = resp.json()
            print(f"   ✓ JSON with {len(data) if isinstance(data, list) else 'unknown'} items")
            if isinstance(data, list) and len(data) > 0:
                print(f"   Sample: {data[0]}")
        else:
            print(f"   Preview: {resp.text[:200]}")
        
        # Try closed positions
        print("\n3. /closed-positions:")
        resp = await client.get(f"{base}/closed-positions?user={TRADER}")
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"   ✓ Response")
        
        # Try user trades endpoint
        print("\n4. /user/trades:")
        resp = await client.get(f"{base}/user/trades?user={TRADER}")
        print(f"   Status: {resp.status_code}")
        print(f"   Preview: {resp.text[:200]}")

asyncio.run(test())
