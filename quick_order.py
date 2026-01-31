#!/usr/bin/env python3
"""
Quick order test - just edit TOKEN_ID and run.
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from src.services.clob_client import PolymarketCLOBClient


# EDIT THIS TOKEN ID - Get from any Polymarket market URL or network tab
TOKEN_ID = os.getenv("TEST_TOKEN_ID", "")

if not TOKEN_ID:
    print("=" * 60)
    print("POLYMARKET QUICK ORDER TEST")
    print("=" * 60)
    print("""
TO TEST: Add a token ID to your .env file:

1. Go to polymarket.com
2. Find an active market (e.g., "Will Trump win in 2026?")
3. Open browser Developer Tools (Cmd+Option+I)
4. Go to Network tab
5. Refresh page
6. Look for requests with "clob" or "token" in the name
7. Copy the token ID (starts with 0x...)

Or add to .env:
    TEST_TOKEN_ID=0x1234567890abcdef...

Then run: python3 quick_order.py
    """)
else:
    async def test():
        print("=" * 60)
        print("PLACING REAL ORDER")
        print("=" * 60)
        
        client = PolymarketCLOBClient(
            api_key=os.getenv("POLYMARKET_API_KEY"),
            secret_key=os.getenv("POLYMARKET_SECRET_KEY"),
            passphrase=os.getenv("POLYMARKET_PASSPHRASE"),
            wallet_address=os.getenv("PROXY_WALLET"),
            private_key=os.getenv("PRIVATE_KEY")
        )
        
        print(f"Token: {TOKEN_ID[:20]}...")
        print(f"Wallet: {os.getenv('PROXY_WALLET')[:10]}...")
        print(f"Balance: ~$433 USDC")
        print()
        print("Placing $1 test order...")
        
        result = await client.place_order(
            token_id=TOKEN_ID,
            side="buy",
            size=1.0,
            price=0.50,
            order_type="limit",
            time_in_force="FOK"
        )
        
        print(f"\nResult:")
        print(f"  Success: {result.success}")
        print(f"  Order ID: {result.order_id}")
        print(f"  Error: {result.error}")
        
        await client.close()
        
        if result.success:
            print("\n🎉 ORDER PLACED SUCCESSFULLY!")
        else:
            print("\n❌ Order failed - check error above")
    
    asyncio.run(test())
