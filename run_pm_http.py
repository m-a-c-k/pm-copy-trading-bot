#!/usr/bin/env python3
"""
PM Copy Bot - Copies SAME whale trades as Kalshi but executes on PM
Uses HTTP API (same as Kalshi) instead of WebSocket
"""

import os
import asyncio
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs

load_dotenv()

# Same traders as Kalshi bot
TRADERS = [
    "0xc257ea7e3a81c7d16ba3225ba1b2c26b224b2c34",  # rustin
    "0xaa0759245548f353f693c1b4401537781bae78f0",  # mrsparky  
    "0xd0b4c4c0234219f1dd41c9f6c0c798df95bc99d5",  # FollowMeABC123
    "0x5c3a1a60b5a8a051351cd0c88e1139311684a471",  # Additional whale
]

PM_API = "https://data-api.polymarket.com/activity"
FETCH_INTERVAL = 3  # Same as Kalshi


class PMHTTPBot:
    """PM bot using HTTP API (same as Kalshi)."""
    
    def __init__(self):
        self.positions = {}
        self.total_exposure = 0.0
        self.max_position = float(os.getenv("PM_MAX_POSITION_SIZE", "2.0"))
        self.max_total = float(os.getenv("PM_MAX_TOTAL_EXPOSURE", "10.0"))
        self.dry_run = os.getenv("PM_DRY_RUN", "true").lower() == "true"
        self.seen_trades = set()
        self.setup_clob()
        
    def setup_clob(self):
        """Setup CLOB client for order execution."""
        try:
            creds = ApiCreds(
                api_key=os.getenv("POLYMARKET_BUILDER_API_KEY"),
                api_secret=os.getenv("POLYMARKET_BUILDER_SECRET"),
                api_passphrase=os.getenv("POLYMARKET_BUILDER_PASSPHRASE")
            )
            
            self.client = ClobClient(
                host="https://clob.polymarket.com",
                key=os.getenv("PRIVATE_KEY"),
                chain_id=137,
                creds=creds
            )
            print("✓ PM CLOB Client ready")
        except Exception as e:
            print(f"⚠️ CLOB client not initialized: {e}")
            self.client = None
    
    def fetch_whale_trades(self, wallet):
        """Fetch trades from PM API (same as Kalshi)."""
        try:
            resp = requests.get(
                PM_API,
                params={"user": wallet, "limit": 20, "status": "open"},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Accept": "application/json",
                    "Origin": "https://polymarket.com",
                    "Referer": "https://polymarket.com/"
                },
                timeout=30
            )
            
            if resp.ok:
                data = resp.json()
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("activity", []) or []
            return []
        except Exception as e:
            print(f"Error fetching: {e}")
            return []
    
    async def execute_trade(self, trade):
        """Execute trade on PM."""
        title = trade.get("title", "Unknown")
        size = float(trade.get("size", 0))
        side = trade.get("side", "BUY")
        outcome = trade.get("outcome", "yes")
        
        # Calculate position
        our_size = min(size * 0.05, self.max_position)
        if our_size < 0.5:
            return False, "Too small"
        
        if self.total_exposure + our_size > self.max_total:
            return False, "Max exposure"
        
        print(f"\n🎯 Copying on PM: {title[:50]}")
        print(f"   Whale: ${size:.2f} | Us: ${our_size:.2f}")
        
        if self.dry_run:
            print(f"   🧪 DRY RUN - Would trade ${our_size:.2f}")
            self.total_exposure += our_size
            return True, "dry_run"
        
        # TODO: Execute real trade via CLOB
        print(f"   📤 LIVE - Trading ${our_size:.2f}")
        self.total_exposure += our_size
        return True, "live"
    
    async def run(self):
        """Main loop - same as Kalshi."""
        print("="*60)
        print("PM COPY BOT - Same Trades as Kalshi")
        print("="*60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Max per trade: ${self.max_position}")
        print(f"Max total: ${self.max_total}")
        print(f"Monitoring {len(TRADERS)} whales...")
        print("-"*60)
        
        scan_count = 0
        
        try:
            while True:
                scan_count += 1
                all_trades = []
                
                # Fetch from all traders (same as Kalshi)
                for trader in TRADERS:
                    trades = self.fetch_whale_trades(trader)
                    for t in trades:
                        t['_trader'] = trader
                    all_trades.extend(trades)
                
                # Filter new trades
                new_trades = []
                for trade in all_trades:
                    trade_id = trade.get("transactionHash") or trade.get("id")
                    if trade_id and trade_id not in self.seen_trades:
                        self.seen_trades.add(trade_id)
                        new_trades.append(trade)
                
                if new_trades:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Found {len(new_trades)} trades")
                    
                    for trade in new_trades:
                        success, msg = await self.execute_trade(trade)
                        status = "✓" if success else "✗"
                        print(f"   {status} {trade.get('title', 'Unknown')[:40]} - {msg}")
                    
                    print(f"   📊 Total PM exposure: ${self.total_exposure:.2f}")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning... ({scan_count} scans)", end="\r")
                
                await asyncio.sleep(FETCH_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\nStopped.")


if __name__ == "__main__":
    bot = PMHTTPBot()
    asyncio.run(bot.run())
