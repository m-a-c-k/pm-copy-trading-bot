#!/usr/bin/env python3
"""Check Polymarket wallet balance."""

import asyncio
import httpx
import os

WALLET = "0x3854c129cd856ee518bf0661792e01ef1f2f586a"

async def check():
    print("=" * 50)
    print("WALLET CHECK")
    print("=" * 50)
    print(f"Wallet: {WALLET}")
    print()
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Try Polymarket API
        resp = await client.get(f"https://api.polymarket.com/api/wallet/balances?wallet={WALLET}")
        print(f"API Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            print(f"Response: {resp.text[:500]}")
        else:
            print(f"Error: {resp.text[:200]}")
        
        # Try Alchemy for on-chain balance
        resp2 = await client.post(
            "https://polygon-mainnet.g.alchemy.com/v2/5K6CVc1EkJsLj9TLjktjs",
            json={
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [WALLET, "latest"],
                "id": 1
            }
        )
        print(f"\nOn-chain balance (Wei): {resp2.json().get('result', '0')}")
        
        # USDC contract on Polygon
        usdc_contract = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
        balance_data = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{
                "to": usdc_contract,
                "data": f"0x70a08231000000000000000000000000{WALLET[2:].lower()}"
            }, "latest"],
            "id": 1
        }
        resp3 = await client.post(
            "https://polygon-mainnet.g.alchemy.com/v2/5K6CVc1EkJsLj9TLjktjs",
            json=balance_data
        )
        print(f"USDC balance (raw): {resp3.json().get('result', '0')}")

asyncio.run(check())
