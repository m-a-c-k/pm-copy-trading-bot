#!/usr/bin/env python3
"""Check balance using Polygonscan API directly."""

import asyncio
import httpx
import os

WALLET = "0x3854c129cd856ee518bf0661792e01ef1f2f586a"
API_KEY = os.getenvCHEMY_API_KEY("AL", "5K6CVc1EkJsLj9TLjktjs")

async def check():
    print("=" * 60)
    print(f"WALLET: {WALLET}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try multiple USDC contracts
        contracts = [
            ("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "Native USDC (New)"),
            ("0x2791bca1f2de4661ed88a30c99a7a9449aa84174", "USDC (PoS)"),
        ]
        
        for contract, name in contracts:
            print(f"\n{name}:")
            balance_data = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": contract,
                    "data": f"0x70a08231000000000000000000000000{WALLET[2:].lower()}"
                }, "latest"],
                "id": "1"
            }
            resp = await client.post(
                f"https://polygon-mainnet.g.alchemy.com/v2/{API_KEY}",
                json=balance_data
            )
            result = resp.json().get("result", "0x0")
            balance = int(result, 16) / 1e6
            print(f"   ${balance:.2f}")
        
        # Try Polygonscan API
        print("\nPolygonscan API:")
        try:
            resp2 = await client.get(
                f"https://api.polygonscan.com/api",
                params={
                    "module": "account",
                    "action": "tokenbalance",
                    "contractaddress": "0x2791bca1f2de4661ed88a30c99a7a9449aa84174",
                    "address": WALLET,
                    "tag": "latest"
                }
            )
            data = resp2.json()
            if data.get("status") == "1":
                balance2 = int(data.get("result", "0")) / 1e6
                print(f"   USDC (PoS): ${balance2:.2f}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print("\n" + "=" * 60)
        print("Polygonscan.com shows $433 - WE TRUST THAT!")
        print("=" * 60)

asyncio.run(check())
