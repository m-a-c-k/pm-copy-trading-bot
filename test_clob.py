#!/usr/bin/env python3
"""Test CLOB order placement with proper signing."""

import asyncio
import json
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

WALLET_ADDRESS = os.getenv("PROXY_WALLET", "0x3854c129cd856ee518bf0661792e01ef1f2f586a")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "")
POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY", "")


async def test_clob_connection():
    """Test CLOB connection and order placement."""
    print("=" * 60)
    print("Testing Polymarket CLOB Connection")
    print("=" * 60)

    print(f"\nWallet: {WALLET_ADDRESS}")
    print(f"API Key: {POLYMARKET_API_KEY[:20]}..." if POLYMARKET_API_KEY else "API Key: None")
    print(f"RPC: Alchemy (key: {ALCHEMY_API_KEY[:10]}...)" if ALCHEMY_API_KEY else "RPC: None")

    from src.services.trade_executor import PolymarketClient

    client = PolymarketClient(
        wallet_address=WALLET_ADDRESS,
        private_key=PRIVATE_KEY
    )

    print(f"\nConnected: {client.w3.is_connected()}")

    nonce = await client.get_nonce()
    print(f"Nonce: {nonce}")

    await client.close()

    return nonce


async def test_small_order():
    """Test placing a small order."""
    print("\n" + "=" * 60)
    print("Testing Small Order Placement")
    print("=" * 60)

    from src.services.trade_executor import PolymarketClient

    client = PolymarketClient(
        wallet_address=WALLET_ADDRESS,
        private_key=PRIVATE_KEY
    )

    print("\nPlacing test order...")
    print("Token: 0x4e788e85b6c2a2bf4c4c7e846e3d14c5f1f9b8aa (Example)")
    print("Side: buy")
    print("Size: 1.00 USDC")
    print("Price: 0.50")

    result = await client.place_order(
        token_id="0x4e788e85b6c2a2bf4c4c7e846e3d14c5f1f9b8aa",
        side="buy",
        size=1.0,
        price=0.50
    )

    print(f"\nResult:")
    print(json.dumps(result, indent=2))

    await client.close()

    return result


async def main():
    """Main test function."""
    try:
        nonce = await test_clob_connection()

        if nonce:
            result = await test_small_order()

            if result.get("status") == "SUBMITTED":
                print("\n✅ Order placed successfully!")
            else:
                print(f"\n⚠️ Order status: {result.get('status')}")
                if result.get("error"):
                    print(f"Error: {result.get('error')}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
