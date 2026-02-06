#!/usr/bin/env python3
"""Test PM with real tiny order."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Set tiny limits for testing
os.environ['PM_DRY_RUN'] = 'false'
os.environ['PM_MAX_POSITION_SIZE'] = '1.0'  # $1 max
os.environ['PM_MAX_TOTAL_EXPOSURE'] = '5.0'  # $5 total

from src.services.pm_executor import PolymarketCopyExecutor, PMCopyConfig

async def test_real_trade():
    print("="*60)
    print("Testing PM with REAL order ($1 max)")
    print("="*60)
    
    config = PMCopyConfig.from_env()
    executor = PolymarketCopyExecutor(config)
    
    if not config.enabled:
        print("\n❌ PM not enabled")
        return
    
    # Test with tiny whale trade
    test_trade = {
        "market": {"title": "Test Market - DO NOT COPY", "id": "test-123"},
        "tokenId": "0x0",
        "side": "buy",
        "outcome": "yes",
        "amount": 10.0,  # Whale bet $10
        "_trader_address": "0xtest"
    }
    
    result = await executor.execute_copy_trade(test_trade)
    print(f"\nResult: {result}")
    
    await executor.close()

if __name__ == "__main__":
    asyncio.run(test_real_trade())
