#!/usr/bin/env python3
"""Test PM order placement with Builder API - SAFE test with $1"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Check credentials
WALLET = os.getenv("PROXY_WALLET", "")
API_KEY = os.getenv("POLYMARKET_BUILDER_API_KEY", "")
SECRET = os.getenv("POLYMARKET_BUILDER_SECRET", "")
PASSPHRASE = os.getenv("POLYMARKET_BUILDER_PASSPHRASE", "")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
ALCHEMY_KEY = os.getenv("ALCHEMY_API_KEY", "")

async def test_pm_order():
    """Place a small test order on PM."""
    
    # Validate setup
    if not all([WALLET, API_KEY, SECRET, PRIVATE_KEY, ALCHEMY_KEY]):
        print("❌ Missing credentials!")
        return
    
    print("="*60)
    print("PM Order Test - Builder API")
    print("="*60)
    print(f"Wallet: {WALLET[:10]}...")
    print(f"Builder: {API_KEY[:20]}...")
    
    # Use the existing PolymarketClient from trade_executor
    try:
        from src.services.trade_executor import PolymarketClient
        
        print("\n1. Initializing PM Client...")
        client = PolymarketClient(
            wallet_address=WALLET,
            private_key=PRIVATE_KEY
        )
        print("   ✓ Client initialized")
        
        # Get nonce
        print("\n2. Getting nonce...")
        nonce = await client.get_nonce()
        print(f"   ✓ Nonce: {nonce}")
        
        # Find a cheap market to test
        print("\n3. Finding test market...")
        print("   Looking for low-price market...")
        
        # Test with a real token ID from a cheap market
        # This is a test token - replace with actual from PM
        test_token = "0x4e788e85b6c2a2bf4c4c7e846e3d14c5f1f9b8aa"  # Example
        
        print("\n4. Placing $1 test order...")
        print("   Token: Example token")
        print("   Side: buy")
        print("   Size: 1.00 USDC")
        print("   Price: 0.01 (1 cent)")
        
        # Note: This uses the existing client but needs Builder headers
        # The actual implementation needs to add Builder auth headers
        
        print("\n⚠️  IMPORTANT:")
        print("   Before placing orders, you need to:")
        print("   1. Set USDC allowance on PM Exchange contract")
        print("   2. Add Builder auth headers to requests")
        print("   3. Use actual token ID from PM market")
        
        await client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pm_order())
