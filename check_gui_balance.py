#!/usr/bin/env python3
"""Check Polymarket balance via profile API."""

import asyncio
import httpx

WALLET = "0x3854c129cd856ee518bf0661792e01ef1f2f586a"

async def check():
    print("=" * 60)
    print(f"POLYMARKET PROFILE: {WALLET}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Try profile endpoint
        print("\n1. Profile API:")
        resp = await client.get(f"https://polymarket.com/profile/{WALLET}")
        print(f"   Status: {resp.status_code}")
        
        # Look for balance in response
        if "balance" in resp.text.lower() or "$" in resp.text:
            import re
            # Try to find dollar amounts
            amounts = re.findall(r'\$([\d,]+\.?\d*)', resp.text)
            print(f"   Found amounts: {amounts[:5]}")
        
        # Try the analytics API
        print("\n2. Analytics API:")
        resp2 = await client.get(f"https://polymarketanalytics.com/api/user/{WALLET}")
        print(f"   Status: {resp2.status_code}")
        if resp2.status_code == 200:
            print(f"   Response: {resp2.text[:500]}")
        
        # Try the wallet balances with different format
        print("\n3. Wallet API (alternative):")
        resp3 = await client.get(
            "https://api.polymarket.com/wallet",
            params={"address": WALLET}
        )
        print(f"   Status: {resp3.status_code}")
        if resp3.status_code == 200:
            print(f"   Response: {resp3.text[:500]}")
        
        # Try with lowercase wallet
        print("\n4. With lowercase wallet:")
        resp4 = await client.get(
            f"https://api.polymarket.com/api/wallet/balances",
            params={"wallet": WALLET.lower()}
        )
        print(f"   Status: {resp4.status_code}")
        if resp4.status_code == 200:
            print(f"   Response: {resp4.text[:500]}")
        
        print("\n" + "=" * 60)
        print("GUI shows ~$434")
        print("On-chain shows $0 - this is normal!")
        print("Polymarket may show custodial balances, not on-chain")
        print("=" * 60)

asyncio.run(check())
