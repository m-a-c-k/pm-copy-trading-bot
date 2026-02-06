#!/usr/bin/env python3
"""Test PM CLOB trading with Builder API keys."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Builder credentials from your PM profile
BUILDER_API_KEY = os.getenv("POLYMARKET_BUILDER_API_KEY", "")
BUILDER_SECRET = os.getenv("POLYMARKET_BUILDER_SECRET", "")
BUILDER_PASSPHRASE = os.getenv("POLYMARKET_BUILDER_PASSPHRASE", "")

# Your wallet info
WALLET_ADDRESS = os.getenv("PROXY_WALLET", "")  # Your MetaMask address with USDC
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")  # For signing orders

async def test_builder_auth():
    """Test if Builder keys work for CLOB API."""
    import httpx
    
    print("Testing PM CLOB with Builder API keys...")
    print(f"Wallet: {WALLET_ADDRESS[:10]}..." if WALLET_ADDRESS else "Wallet: NOT SET")
    print(f"Builder Key: {BUILDER_API_KEY[:20]}..." if BUILDER_API_KEY else "Builder Key: NOT SET")
    
    if not all([BUILDER_API_KEY, BUILDER_SECRET, WALLET_ADDRESS]):
        print("\n❌ Missing credentials! Need:")
        print("  - POLYMARKET_BUILDER_API_KEY")
        print("  - POLYMARKET_BUILDER_SECRET") 
        print("  - POLYMARKET_BUILDER_PASSPHRASE (optional)")
        print("  - PROXY_WALLET (your MetaMask address)")
        return
    
    # Test 1: Get markets (public, no auth needed)
    print("\n1. Testing public endpoint (markets)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://clob.polymarket.com/markets")
        if resp.status_code == 200:
            markets = resp.json()
            print(f"   ✓ Got {len(markets.get('data', []))} markets")
        else:
            print(f"   ✗ Failed: {resp.status_code}")
    
    # Test 2: Check wallet balance/orders (requires auth)
    print("\n2. Testing authenticated endpoint (orders)...")
    # This would require the CLOB client with your builder credentials
    print("   (Requires CLOB client setup)")
    
    # Test 3: Check if we can place a small test order
    print("\n3. Next step: Place a $1 test order")
    print("   Need to:")
    print("   a. Set USDC allowance on Exchange contract")
    print("   b. Create signed order with private key")
    print("   c. Submit via CLOB API with Builder auth")

if __name__ == "__main__":
    asyncio.run(test_builder_auth())
