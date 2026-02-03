#!/usr/bin/env python3
"""
PM Copy Trading Bot with Kalshi Copy Mode

Mirrors Polymarket whale trades to Kalshi.

Usage:
    python3 run_kalshi_copy.py --dry-run     # Test without executing
    python3 run_kalshi_copy.py --live        # Real trading
    python3 run_kalshi_copy.py --status      # Show status
"""

import os
import sys
import time
import json
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.services.kalshi_client import KalshiClient, KalshiConfig
from src.services.kalshi_executor import KalshiExecutor, KalshiCopyConfig, create_executor
from src.services.market_matcher import MarketMatcher
from src.services.kelly_calculator import KellyCalculator
from src.services.risk_manager import RiskManager

from src.config.traders import get_active_traders

POLYMARKET_ACTIVITY_API = "https://data-api.polymarket.com/activity"
FETCH_INTERVAL = 3


def fetch_whale_trades(wallet_address: str, limit: int = 20) -> list:
    """Fetch recent trades from a specific wallet."""
    try:
        resp = requests.get(
            POLYMARKET_ACTIVITY_API,
            params={
                "user": wallet_address,
                "limit": limit,
                "status": "open"
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if resp.ok:
            data = resp.json()
            return data.get("activity", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"Error fetching whale trades: {e}")
    return []


def main():
    parser = argparse.ArgumentParser(description="PM Copy Trading Bot - Kalshi Mode")
    parser.add_argument("--dry-run", action="store_true", help="Test mode (no real trades)")
    parser.add_argument("--live", action="store_true", help="Real trading mode")
    parser.add_argument("--status", action="store_true", help="Show status and exit")
    parser.add_argument("--test", action="store_true", help="Run integration test")
    args = parser.parse_args()

    config = KalshiCopyConfig.from_env()
    kalshi_config = KalshiConfig.from_env()

    if not kalshi_config.enabled:
        print("❌ Kalshi not configured. Add KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PEM to .env")
        sys.exit(1)

    if args.status:
        executor = create_executor(dry_run=True)
        status = executor.get_status()
        print("=" * 50)
        print("KALSHI COPY TRADING STATUS")
        print("=" * 50)
        print(f"Enabled: {status['enabled']}")
        print(f"Dry Run: {status['dry_run']}")
        print(f"Bankroll: ${status['bankroll']}")
        print(f"Kalshi Balance: ${status['balance']}")
        print(f"Whale Stats: {status['whale_stats']}")
        sys.exit(0)

    if args.test:
        print("Running integration test...")
        executor = create_executor(dry_run=True)

        # Test with sample trade
        sample_trade = {
            "market": {
                "id": "pm-123",
                "title": "Will Syracuse beat North Carolina?",
                "slug": "cbb-syr-unc-2026-02-01"
            },
            "tokenId": "abc123",
            "side": "buy",
            "amount": 150,
            "outcome": "yes"
        }

        pm_trade = executor.matcher.parse_pm_trade(sample_trade)
        if pm_trade:
            result = executor.execute_copy_trade(sample_trade, pm_trade)
            print(f"\nTest result: {'✓ PASS' if result.success else '✗ FAIL'}")
            if result.success:
                print(f"  Position: ${result.position_size:.2f}")
                print(f"  Side: {result.side}")
            else:
                print(f"  Error: {result.error}")
        sys.exit(0)

    dry_run = not args.live and config.dry_run

    print("=" * 60)
    print("PM COPY TRADING BOT - KALSHI MODE")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    traders = get_active_traders()
    print(f"Traders: {len(traders)}")
    for t in traders:
        print(f"  - {t[:12]}...")
    print(f"Interval: {FETCH_INTERVAL}s")
    print("-" * 60)

    executor = create_executor(dry_run=dry_run)
    
    # Skip slow initial balance check - show basic info
    print("-" * 60)
    print(f"Bankroll: ${executor.config.bankroll}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print()

    print("Monitoring for whale trades...")
    seen_trades = set()
    scan_count = 0
    spinner = "|/-\\"

    try:
        while True:
            scan_count += 1
            all_trades = []
            for trader in traders:
                trades = fetch_whale_trades(trader, limit=20)
                all_trades.extend(trades)

            new_trades = []
            for trade in all_trades:
                trade_id = trade.get("conditionId") or trade.get("transactionHash") or trade.get("id")
                if trade_id and trade_id not in seen_trades:
                    seen_trades.add(trade_id)
                    new_trades.append(trade)

            if new_trades:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Found {len(new_trades)} new whale trade(s)")

                sports_trades = []
                non_sports_trades = []
                for trade in new_trades:
                    # API returns flat structure - check both nested and flat
                    market_info = trade.get("market", {})
                    market_title = (market_info.get("title") or trade.get("title") or trade.get("question") or "Unknown")
                    slug = (market_info.get("slug") or trade.get("slug") or "")
                    size = float(trade.get("amount") or trade.get("size") or 0)
                    
                    # Create a normalized trade dict for parsing
                    normalized_trade = {
                        **trade,
                        "market": {
                            "title": market_title,
                            "slug": slug,
                            "id": market_info.get("id") or trade.get("conditionId", "")
                        }
                    }
                    
                    # Check if sports
                    pm_trade = executor.matcher.parse_pm_trade(normalized_trade)
                    if pm_trade and pm_trade.sport:
                        sports_trades.append(normalized_trade)
                        print(f"  🏈 {market_title[:50]}... (${size})")
                    else:
                        non_sports_trades.append(market_title)
                        print(f"  ⏭️ {market_title[:50]}... (non-sports, skipped)")

                if non_sports_trades:
                    print(f"  ↪ Skipped {len(non_sports_trades)} non-sports markets")

                results = executor.process_whale_trades(sports_trades)
                success_count = sum(1 for r in results if r.success)
                print(f"  → Copied {success_count}/{len(results)} trades to Kalshi")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning... ({scan_count} scans, {len(seen_trades)} seen) ", end="\r")

            time.sleep(FETCH_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nStopping bot...")
        sys.exit(0)


if __name__ == "__main__":
    main()
