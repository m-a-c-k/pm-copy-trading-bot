#!/usr/bin/env python3
"""
Test placing a real order on Polymarket.
Requires: USDC in wallet, valid market token ID
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()


async def test_place_order():
    from src.services.clob_client import PolymarketCLOBClient, OrderResult
    
    print("=" * 60)
    print("POLYMARKET ORDER TEST")
    print("=" * 60)
    
    # Check credentials
    api_key = os.getenv("POLYMARKET_API_KEY")
    secret_key = os.getenv("POLYMARKET_SECRET_KEY")
    passphrase = os.getenv("POLYMARKET_PASSPHRASE")
    wallet = os.getenv("PROXY_WALLET")
    private_key = os.getenv("PRIVATE_KEY")
    
    print(f"API Key: {api_key[:20]}...")
    print(f"Wallet: {wallet}")
    print()
    
    if not api_key or "your_polymarket" in api_key:
        print("❌ Missing Polymarket API credentials")
        return
    
    # Create client
    client = PolymarketCLOBClient(
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        wallet_address=wallet,
        private_key=private_key
    )
    
    # Check balances first
    print("📊 Checking USDC balance...")
    balances = await client.get_balances()
    usdc_balance = balances.get("USDC", 0)
    print(f"   USDC: ${usdc_balance:.2f}")
    
    if usdc_balance < 1:
        print("❌ Need at least $1 USDC to test")
        await client.close()
        return
    
    # Test order on a known market (using a sample token)
    # Note: You'll need to find a real token ID from Polymarket
    test_token_id = os.getenv("TEST_TOKEN_ID", "")
    
    if test_token_id:
        print(f"\n📝 Placing test order...")
        print(f"   Token: {test_token_id}")
        print(f"   Side: BUY")
        print(f"   Size: $1.00")
        print(f"   Price: $0.50")
        
        result = await client.place_order(
            token_id=test_token_id,
            side="buy",
            size=1.0,
            price=0.50,
            order_type="limit",
            time_in_force="FOK"  # Fill or Kill
        )
        
        print(f"\n✅ Order Result:")
        print(f"   Success: {result.success}")
        print(f"   Order ID: {result.order_id}")
        print(f"   Error: {result.error}")
        
        if result.success:
            print(f"\n🎉 Order placed successfully!")
            print(f"   Order ID: {result.order_id}")
            print(f"   Size: ${result.size}")
            print(f"   Filled Price: ${result.filled_price}")
        else:
            print(f"\n⚠️ Order failed: {result.error}")
    else:
        print("\n📋 To test real orders:")
        print("1. Find a market on Polymarket")
        print("2. Get the token ID from URL or API")
        print("3. Add TEST_TOKEN_ID to .env")
        print("4. Run this test again")
        print()
        print("Example .env:")
        print("   TEST_TOKEN_ID=0x4e6f0...e4d8")
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(test_place_order())
