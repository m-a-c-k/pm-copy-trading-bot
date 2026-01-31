#!/usr/bin/env python3
"""Check wallet on all networks."""

import asyncio
import httpx

WALLET = "0x3854c129cd856ee518bf0661792e01ef1f2f586a"

async def check():
    print("=" * 60)
    print(f"CHECKING WALLET: {WALLET}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Polygon
        print("\n📍 POLYGON:")
        resp = await client.post(
            "https://polygon-mainnet.g.alchemy.com/v2/5K6CVc1EkJsLj9TLjktjs",
            json={
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [WALLET, "latest"],
                "id": 1
            }
        )
        matic = int(resp.json().get("result", "0x0"), 16) / 1e18
        print(f"   MATIC: {matic:.4f}")
        
        # USDC on Polygon
        resp2 = await client.post(
            "https://polygon-mainnet.g.alchemy.com/v2/5K6CVc1EkJsLj9TLjktjs",
            json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
                    "data": f"0x70a08231000000000000000000000000{WALLET[2:].lower()}"
                }, "latest"],
                "id": 2
            }
        )
        poly_usdc = int(resp2.json().get("result", "0x0"), 16) / 1e6
        print(f"   USDC: ${poly_usdc:.2f}")
        
        # Ethereum Mainnet
        print("\n🌐 ETHEREUM MAINNET:")
        resp3 = await client.post(
            "https://eth-mainnet.g.alchemy.com/v2/demo",
            json={
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [WALLET, "latest"],
                "id": 3
            }
        )
        eth = int(resp3.json().get("result", "0x0"), 16) / 1e18
        print(f"   ETH: {eth:.4f}")
        
        # USDC on Ethereum
        resp4 = await client.post(
            "https://eth-mainnet.g.alchemy.com/v2/demo",
            json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                    "data": f"0x70a08231000000000000000000000000{WALLET[2:].lower()}"
                }, "latest"],
                "id": 4
            }
        )
        eth_usdc = int(resp4.json().get("result", "0x0"), 16) / 1e6
        print(f"   USDC: ${eth_usdc:.2f}")
        
        print("\n" + "=" * 60)
        if poly_usdc > 0:
            print(f"✅ Found ${poly_usdc:.2f} USDC on POLYGON")
        elif eth_usdc > 0:
            print(f"✅ Found ${eth_usdc:.2f} USDC on ETHEREUM")
            print("⚠️  Bridge to Polygon to trade on Polymarket")
        else:
            print(f"⚠️  No USDC found on main chains")
        print("=" * 60)

asyncio.run(check())
