#!/usr/bin/env python3
"""
PM Copy Bot - Using Official py-clob-client SDK
Replaces the broken data-api approach with proper CLOB client
"""

import os
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

load_dotenv()

# PM Credentials
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
API_KEY = os.getenv("POLYMARKET_BUILDER_API_KEY", "")
API_SECRET = os.getenv("POLYMARKET_BUILDER_SECRET", "")
API_PASSPHRASE = os.getenv("POLYMARKET_BUILDER_PASSPHRASE", "")

# Settings
CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon mainnet
FETCH_INTERVAL = 30  # Seconds between scans


class PMOfficialBot:
    """PM copy trading using official CLOB client."""
    
    def __init__(self):
        self.client = None
        self.positions = {}
        self.total_exposure = 0.0
        self.max_position = float(os.getenv("PM_MAX_POSITION_SIZE", "2.0"))
        self.max_total = float(os.getenv("PM_MAX_TOTAL_EXPOSURE", "10.0"))
        self.dry_run = os.getenv("PM_DRY_RUN", "true").lower() == "true"
        self.setup_client()
        
    def setup_client(self):
        """Initialize CLOB client with Builder credentials."""
        try:
            creds = ApiCreds(
                api_key=API_KEY,
                api_secret=API_SECRET,
                api_passphrase=API_PASSPHRASE
            )
            
            self.client = ClobClient(
                host=CLOB_HOST,
                key=PRIVATE_KEY,
                chain_id=CHAIN_ID,
                creds=creds
            )
            
            print("✓ PM CLOB Client initialized")
            print(f"  Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
            print(f"  Max per trade: ${self.max_position}")
            print(f"  Max total: ${self.max_total}")
            
        except Exception as e:
            print(f"❌ Failed to init client: {e}")
            self.client = None
    
    def get_whale_trades(self):
        """Fetch whale trades using CLOB client."""
        if not self.client:
            return []
        
        try:
            # Try to get recent trades via client
            # Note: py-clob-client may not have direct whale trade API
            # We may need to use a different endpoint or approach
            
            # For now, return empty - will implement proper fetching
            return []
            
        except Exception as e:
            print(f"Error fetching trades: {e}")
            return []
    
    async def run(self):
        """Main bot loop."""
        if not self.client:
            print("❌ Cannot run - client not initialized")
            return
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] PM Bot started")
        print(f"Monitoring for whale trades...\n")
        
        scan_count = 0
        seen_trades = set()
        
        try:
            while True:
                scan_count += 1
                
                # Fetch trades
                trades = self.get_whale_trades()
                
                # Process new trades
                new_trades = [t for t in trades if t.get('id') not in seen_trades]
                for t in new_trades:
                    seen_trades.add(t.get('id'))
                
                if new_trades:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Found {len(new_trades)} new trade(s)")
                    # TODO: Process trades
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning... ({scan_count} scans)", end="\r")
                
                await asyncio.sleep(FETCH_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\nStopping PM Bot...")


async def main():
    """Start PM bot."""
    print("="*60)
    print("PM COPY BOT - Official CLOB Client")
    print("="*60)
    
    bot = PMOfficialBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
