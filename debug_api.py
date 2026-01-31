#!/usr/bin/env python3
"""Debug Polymarket API endpoints."""

import asyncio
import httpx

TRADER = "0xc257ea7e3a81ca8e16df8935d44d513959fa358e"
WALLET = "0x3854c129cd856ee518bf0661792e01ef1f2f586a"

async def debug():
    print("=" * 60)
    print("DEBUGGING POLYMARKET API")
    print("=" * 60)
    print(f"Trader: {TRADER}")
    print(f"Wallet: {WALLET}")
    print()
    
    base_urls = [
        "https://api.polymarket.com",
        "https://api.clob.polymarket.com", 
        "https://clob.polymarket.com",
        "https://polymarket.com/api",
    ]
    
    endpoints = [
        f"/api/core/users/{TRADER}/activity",
        f"/api/core/users/{TRADER}/history",
        f"/api/users/{TRADER}/activity",
        f"/users/{TRADER}/activity",
        f"/user/{TRADER}/activity",
    ]
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for base in base_urls:
            print(f"Base URL: {base}")
            for endpoint in endpoints:
                url = base + endpoint
                try:
                    resp = await client.get(url, params={"limit": 5})
                    status = resp.status_code
                    preview = resp.text[:100].replace('\n', ' ')
                    print(f"  {endpoint:<35} → {status} | {preview}")
                except Exception as e:
                    print(f"  {endpoint:<35} → Error: {e}")
            print()

if __name__ == "__main__":
    asyncio.run(debug())
