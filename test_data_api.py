#!/usr/bin/env python3
"""Test Polymarket Data API for user trades."""

import asyncio
import httpx

TRADER = "0xc257ea7e3a81ca8e16df8935d44d513959fa358e"
WALLET = "0x3854c129cd856ee518bf0661792e01ef1f2f586a"

async def test():
    print("=" * 60)
    print("TESTING DATA API")
    print("=" * 60)
    print(f"Trader: {TRADER}")
    print()
    
    base = "https://data-api.polymarket.com"
    
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        # Test 1: Get user activity
        print("1. User Activity:")
        resp = await client.get(f"{base}/user-activity", params={"user": TRADER})
        print(f"   /user-activity: {resp.status_code}")
        if resp.status_code == 200:
            print(f"   ✓ Response: {resp.text[:300]}")
        else:
            print(f"   ✗ {resp.text[:200]}")
        
        # Test 2: Get trades
        print("\n2. Get Trades:")
        resp = await client.get(f"{base}/api/core/users/{TRADER}/trades")
        print(f"   /api/core/users/{{user}}/trades: {resp.status_code}")
        print(f"   {resp.text[:300]}")
        
        # Test 3: Get positions
        print("\n3. Get Positions:")
        resp = await client.get(f"{base}/positions", params={"user": WALLET})
        print(f"   /positions?user={{wallet}}: {resp.status_code}")
        print(f"   {resp.text[:300]}")
        
        # Test 4: Get profile
        print("\n4. Get Profile:")
        resp = await client.get(f"{base}/profiles/{WALLET}")
        print(f"   /profiles/{{wallet}}: {resp.status_code}")
        print(f"   {resp.text[:300]}")
        
        # Test 5: Try different paths
        paths = [
            "/activity",
            "/trades",
            "/history", 
            "/user/trades"
        ]
        print("\n5. Trying paths:")
        for path in paths:
            url = f"{base}{path}?user={TRADER}"
            resp = await client.get(url)
            print(f"   {path}: {resp.status_code}")

asyncio.run(test())
