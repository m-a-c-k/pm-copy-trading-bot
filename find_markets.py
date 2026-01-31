#!/usr/bin/env python3
"""Find active Polymarket markets for testing."""

import asyncio
import httpx

async def find_markets():
    print("=" * 60)
    print("FINDING POLYMARKET MARKETS")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Get trending markets
        resp = await client.get(
            "https://api.polymarket.com/markets",
            params={"limit": 5, "active": "true", "orderBy": "volume"}
        )
        
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                markets = data.get("markets", []) if isinstance(data, dict) else []
                
                print(f"\nFound {len(markets)} active markets:\n")
                
                for m in markets[:5]:
                    token_id = m.get("clobTokenId") or m.get("tokenId") or "N/A"
                    print(f"📊 {m.get('question', 'Unknown')[:50]}...")
                    print(f"   ID: {token_id}")
                    print(f"   Price: ${m.get('outcomePrices', ['N/A'])[0] if m.get('outcomePrices') else 'N/A'}")
                    print()
            except Exception as e:
                print(f"Parse error: {e}")
                print(f"Raw: {resp.text[:500]}")
        else:
            print(f"Error: {resp.text[:300]}")

asyncio.run(find_markets())
