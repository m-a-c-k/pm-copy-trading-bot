#!/usr/bin/env python3
"""
PM Copy Bot - Copy whale trades directly on Polymarket
No sports filter - copies ALL markets!
"""

import asyncio
import os
import json
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from src.config.traders import get_active_traders
from src.services.pm_executor import PolymarketCopyExecutor, PMCopyConfig

POLYMARKET_ACTIVITY_API = "https://data-api.polymarket.com/activity"
FETCH_INTERVAL = 15  # Slower polling to avoid Cloudflare


def fetch_whale_trades(wallet_address: str, limit: int = 20) -> list:
    """Fetch recent trades from a specific wallet."""
    import requests
    try:
        # Browser-like headers to avoid Cloudflare detection
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://polymarket.com",
            "Referer": "https://polymarket.com/",
            "Connection": "keep-alive",
        }
        resp = requests.get(
            POLYMARKET_ACTIVITY_API,
            params={"user": wallet_address, "limit": limit, "status": "open"},
            headers=headers,
            timeout=30
        )
        if resp.ok:
            data = resp.json()
            # Handle both list and dict formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("activity", []) or data.get("data", []) or []
            return []
    except Exception as e:
        print(f"Error fetching whale trades: {e}")
    return []


async def main():
    """Main bot loop for PM copy trading."""
    
    print("="*60)
    print("PM COPY BOT - Direct Polymarket Trading")
    print("="*60)
    
    # Check if live trading enabled
    dry_run = os.getenv("PM_DRY_RUN", "true").lower() == "true"
    
    # Initialize executor
    config = PMCopyConfig.from_env()
    config.dry_run = dry_run
    executor = PolymarketCopyExecutor(config)
    
    if not config.enabled:
        print("\n❌ PM trading not enabled")
        print("Add to .env:")
        print("  COPY_TO_POLYMARKET=true")
        print("  PM_DRY_RUN=false (for live trading)")
        return
    
    # Get traders
    traders = get_active_traders()
    print(f"\nMonitoring {len(traders)} whale traders:")
    for t in traders:
        print(f"  - {t[:16]}...")
    
    print(f"\nMode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print(f"Max per trade: ${config.max_position_size}")
    print(f"Max total: ${config.max_total_exposure}")
    print(f"Copies: ALL markets (sports, politics, crypto, etc.)")
    print("-"*60)
    
    # Main loop
    seen_trades = set()
    scan_count = 0
    error_count = 0
    max_errors = 5
    base_delay = FETCH_INTERVAL
    
    try:
        while True:
            scan_count += 1
            all_trades = []
            fetch_success = True
            
            # Fetch trades from all traders
            for trader in traders:
                try:
                    trades = fetch_whale_trades(trader, limit=20)
                    for t in trades:
                        t['_trader_address'] = trader
                    all_trades.extend(trades)
                except Exception as e:
                    fetch_success = False
                    error_count += 1
                    if error_count >= max_errors:
                        print(f"\n⚠️  Too many API errors ({error_count}), backing off...")
                        # Exponential backoff
                        delay = min(base_delay * (2 ** (error_count - max_errors)), 300)  # Max 5 min
                        print(f"   Waiting {delay}s before retry...")
                        await asyncio.sleep(delay)
                        error_count = 0  # Reset after backoff
                    continue
            
            # Reset error count on success
            if fetch_success:
                error_count = max(0, error_count - 1)
            
            # Filter new trades
            new_trades = []
            for trade in all_trades:
                trade_id = trade.get("conditionId") or trade.get("transactionHash") or trade.get("id")
                if trade_id and trade_id not in seen_trades:
                    seen_trades.add(trade_id)
                    new_trades.append(trade)
            
            if new_trades:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Found {len(new_trades)} new whale trade(s)")
                
                # Copy ALL trades (no sports filter!)
                for trade in new_trades:
                    result = await executor.execute_copy_trade(trade)
                    
                    if result.get("success"):
                        if result.get("dry_run"):
                            print(f"  🧪 Would copy ${result.get('size', 0):.2f}")
                        else:
                            print(f"  ✅ Copied ${result.get('size', 0):.2f}")
                    else:
                        print(f"  ⏭️  Skipped: {result.get('error', 'Unknown')}")
                
                status = executor.get_status()
                print(f"  📊 Total exposure: ${status['total_exposure']:.2f}")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning... ({scan_count} scans, {len(seen_trades)} seen)", end="\r")
            
            # Add jitter to avoid detection
            import random
            jitter = random.uniform(0.5, 1.5)
            await asyncio.sleep(FETCH_INTERVAL * jitter)
            
    except KeyboardInterrupt:
        print("\n\nStopping PM Copy Bot...")
        await executor.close()
        print(f"Total trades copied: {len(executor.positions)}")
        print(f"Total exposure: ${executor.total_exposure:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
