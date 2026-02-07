#!/usr/bin/env python3
"""Test PM live trading with $1 order."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("PM LIVE TRADING TEST")
print("="*60)
print(f"Wallet: {os.getenv('PROXY_WALLET', 'NOT SET')[:20]}...")
print(f"Balance: ~$231 USDC")
print("")

# Import after env loaded
from src.services.pm_executor import PolymarketCopyExecutor, PMCopyConfig

async def test_pm_trade():
    """Place a $1 test trade on PM."""
    
    config = PMCopyConfig.from_env()
    config.dry_run = False  # LIVE MODE
    config.max_position_size = 1.0  # $1 max for test
    config.max_total_exposure = 5.0  # $5 total for safety
    
    print(f"Config:")
    print(f"  Dry run: {config.dry_run}")
    print(f"  Max trade: ${config.max_position_size}")
    print(f"  Max total: ${config.max_total_exposure}")
    print("")
    
    executor = PolymarketCopyExecutor(config)
    
    if not config.enabled:
        print("❌ PM not enabled - check .env")
        return
    
    # Create a test trade
    test_trade = {
        "title": "Test Trade - DO NOT EXECUTE",
        "slug": "test-market-123",
        "side": "BUY",
        "outcome": "yes", 
        "usdcSize": 20.0,  # Whale bet $20
        "asset": "0x1234567890abcdef",
        "conditionId": "0xabcdef1234567890",
        "_trader_address": "0xtest123"
    }
    
    print("Placing $1 test order...")
    result = await executor.execute_copy_trade(test_trade)
    
    print(f"\nResult:")
    print(f"  Success: {result.get('success')}")
    print(f"  Order ID: {result.get('order_id', 'N/A')}")
    print(f"  Size: ${result.get('size', 0):.2f}")
    
    if result.get('error'):
        print(f"  Error: {result.get('error')}")
    
    await executor.close()

if __name__ == "__main__":
    confirm = input("Place $1 test order on PM? (yes/no): ")
    if confirm.lower() == "yes":
        asyncio.run(test_pm_trade())
    else:
        print("Cancelled.")
