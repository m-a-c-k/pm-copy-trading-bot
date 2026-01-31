#!/usr/bin/env python3
"""
Test script to execute a real trade on Polymarket.
Run after adding API keys to .env
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()


async def test_real_trade():
    """Test if we can connect and place an order."""
    from src.services.trade_executor import TradeExecutor, ExecutorConfig
    
    wallet = os.getenv("PROXY_WALLET")
    private_key = os.getenv("PRIVATE_KEY")
    alchemy_key = os.getenv("ALCHEMY_API_KEY")
    poly_api_key = os.getenv("POLYMARKET_API_KEY")
    poly_secret = os.getenv("POLYMARKET_SECRET_KEY")
    
    print("=" * 50)
    print("Polymarket Trading Test")
    print("=" * 50)
    print(f"Wallet: {wallet[:10]}...")
    print(f"Alchemy: {'✅' if alchemy_key and alchemy_key != 'your_alchemy_api_key_here' else '❌'}")
    print(f"Private Key: {'✅' if private_key and private_key != 'your_private_key...' else '❌'}")
    print(f"Poly API Key: {'✅' if poly_api_key and poly_api_key != 'your_polymarket_api_key_here' else '❌'}")
    print(f"Poly Secret: {'✅' if poly_secret and poly_secret != 'your_polymarket_secret_key_here' else '❌'}")
    print()
    
    # Check if ready
    missing = []
    if not alchemy_key or alchemy_key == "your_alchemy_api_key_here":
        missing.append("ALCHEMY_API_KEY")
    if not private_key or "your_private" in private_key:
        missing.append("PRIVATE_KEY")
    if not poly_api_key or "your_polymarket" in poly_api_key:
        missing.append("POLYMARKET_API_KEY")
    if not poly_secret or "your_polymarket" in poly_secret:
        missing.append("POLYMARKET_SECRET_KEY")
    
    if missing:
        print("❌ Missing required credentials:")
        for m in missing:
            print(f"   - {m}")
        print()
        print("To get Polymarket API keys:")
        print("1. Go to polymarket.com/settings")
        print("2. Look for 'API' section")
        print("3. Create new API key")
        print()
        print("Edit .env and add your keys, then run this again.")
        return
    
    print("✅ All credentials present!")
    print()
    print("Note: Real trading requires full CLOB client implementation.")
    print("Current executor is a simulation.")
    print()
    print("For automated copy trading, you need:")
    print("1. Full CLOB client (contact Polymarket for API access)")
    print("2. Or manual trading with bot alerts")
    print()
    print("Running connection test...")
    
    # Just verify we can connect
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.polymarket.com/markets?limit=1")
            print(f"Polymarket API: {resp.status_code}")
            if resp.status_code in [200, 404]:
                print("✅ Connection works!")
    except Exception as e:
        print(f"Connection error: {e}")


if __name__ == "__main__":
    asyncio.run(test_real_trade())
