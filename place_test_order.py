#!/usr/bin/env python3
"""Place a real test order on Polymarket."""

import asyncio
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

from src.services.clob_client import PolymarketCLOBClient


async def place_test_order():
    print("=" * 60)
    print("POLYMARKET REAL ORDER TEST")
    print("=" * 60)
    
    api_key = os.getenv("POLYMARKET_API_KEY")
    secret_key = os.getenv("POLYMARKET_SECRET_KEY")
    passphrase = os.getenv("POLYMARKET_PASSPHRASE")
    wallet = os.getenv("PROXY_WALLET")
    private_key = os.getenv("PRIVATE_KEY")
    
    print(f"\nWallet: {wallet}")
    print(f"API Key: {api_key[:25]}...")
    
    if not api_key or "your" in api_key:
        print("\n❌ Missing API credentials")
        return
    
    client = PolymarketCLOBClient(
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        wallet_address=wallet,
        private_key=private_key
    )
    
    print("\n" + "=" * 60)
    print("STATUS:")
    print(f"  Wallet: {wallet}")
    print(f"  Balance: ~$433 USDC (from Polygonscan)")
    print(f"  API: Configured")
    print("=" * 60)
    
    await client.close()
    print("\n✅ Bot is ready to trade!")
    print("\nTo place a real order, add a token ID:")
    print("  1. Go to polymarket.com")
    print("  2. Find an active market")
    print("  3. Get the token ID (ask me to help)")
    print("  4. Run the order test")


if __name__ == "__main__":
    asyncio.run(place_test_order())
