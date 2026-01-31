#!/usr/bin/env python3
"""Verify wallet balance with multiple methods."""

import asyncio
import httpx

WALLET = "0x3854c129cd856ee518bf0661792e01ef1f2f586a"
USDC_CONTRACT = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

async def check():
    print("=" * 60)
    print(f"WALLET: {WALLET}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Method 1: Direct on-chain balance via Alchemy
        print("\n1. Alchemy - Native MATIC balance:")
        resp = await client.post(
            "https://polygon-mainnet.g.alchemy.com/v2/5K6CVc1EkJsLj9TLjktjs",
            json={
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [WALLET, "latest"],
                "id": 1
            }
        )
        result = resp.json().get("result", "0x0")
        matic_balance = int(result, 16) / 1e18
        print(f"   MATIC: {matic_balance:.4f}")
        
        # Method 2: USDC balance via Alchemy
        print("\n2. Alchemy - USDC balance:")
        balance_data = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{
                "to": USDC_CONTRACT,
                "data": f"0x70a08231000000000000000000000000{WALLET[2:].lower()}"
            }, "latest"],
            "id": 1
        }
        resp2 = await client.post(
            "https://polygon-mainnet.g.alchemy.com/v2/5K6CVc1EkJsLj9TLjktjs",
            json=balance_data
        )
        result2 = resp2.json().get("result", "0x0")
        usdc_balance = int(result2, 16) / 1e6
        print(f"   USDC: ${usdc_balance:.2f}")
        
        # Method 3: Polymarket wallet API
        print("\n3. Polymarket Wallet API:")
        resp3 = await client.get(
            f"https://api.polymarket.com/api/wallet/balances?wallet={WALLET}"
        )
        print(f"   Status: {resp3.status_code}")
        if resp3.status_code == 200:
            print(f"   Response: {resp3.text[:300]}")
        else:
            print(f"   Response: {resp3.text[:200]}")
        
        # Method 4: Check Polymarket positions
        print("\n4. Polymarket Positions:")
        resp4 = await client.get(
            f"https://api.polymarket.com/api/positions?user={WALLET}"
        )
        print(f"   Status: {resp4.status_code}")
        if resp4.status_code == 200:
            try:
                data = resp4.json()
                print(f"   Has positions: {len(data) > 0 if isinstance(data, list) else 'unknown'}")
                print(f"   Response: {str(data)[:200]}")
            except:
                print(f"   Response: {resp4.text[:200]}")
        
        print("\n" + "=" * 60)
        if usdc_balance > 0:
            print(f"✅ WALLET HAS ${usdc_balance:.2f} USDC!")
        else:
            print(f"⚠️  Wallet shows $0.00 USDC on-chain")
            print("This means the funds might be on a different chain")
            print("or in a different wallet address.")
        print("=" * 60)

asyncio.run(check())
