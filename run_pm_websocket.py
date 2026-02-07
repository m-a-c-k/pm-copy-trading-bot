#!/usr/bin/env python3
"""
PM Copy Bot - Using RTDS WebSocket for live trades
Replaces blocked HTTP API with WebSocket connection
"""

import os
import json
import asyncio
import websockets
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Settings
RTDS_URL = "wss://ws-live-data.polymarket.com"
TRADERS = [
    "0xc257ea7e3a81c7d16ba3225ba1b2c26b224b2c34",  # rustin
    "0xaa0759245548f353f693c1b4401537781bae78f0",  # mrsparky
    "0xd0b4c4c0234219f1dd41c9f6c0c798df95bc99d5",  # FollowMeABC123
    "0x5c3a1a60b5a8a051351cd0c88e1139311684a471",  # Additional whale
]


class PMWebSocketBot:
    """PM copy trading using RTDS WebSocket."""
    
    def __init__(self):
        self.positions = {}
        self.total_exposure = 0.0
        self.max_position = float(os.getenv("PM_MAX_POSITION_SIZE", "2.0"))
        self.max_total = float(os.getenv("PM_MAX_TOTAL_EXPOSURE", "10.0"))
        self.dry_run = os.getenv("PM_DRY_RUN", "true").lower() == "true"
        self.seen_trades = set()
        
    async def connect(self):
        """Connect to RTDS WebSocket."""
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to PM RTDS...")
            
            async with websockets.connect(RTDS_URL) as ws:
                print(f"✓ Connected to RTDS")
                
                # Subscribe to activity feed (correct format)
                subscribe_msg = {
                    "action": "subscribe",
                    "subscriptions": [
                        {
                            "topic": "activity",
                            "type": "trades"
                        }
                    ]
                }
                await ws.send(json.dumps(subscribe_msg))
                print(f"✓ Subscribed to trades")
                
                # Listen for messages
                async for message in ws:
                    await self.handle_message(message)
                    
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            await asyncio.sleep(5)
            await self.connect()  # Reconnect
    
    async def handle_message(self, message):
        """Process incoming trade."""
        try:
            # Skip empty messages
            if not message:
                return
            data = json.loads(message)
            
            # Check if it's a trade message
            if data.get("type") != "trades":
                return
            
            trade = data.get("payload", {})
            trade_id = trade.get("transactionHash", "")
            
            # Skip if already seen
            if trade_id in self.seen_trades:
                return
            self.seen_trades.add(trade_id)
            
            # Check if from our whales
            trader = trade.get("proxyWallet", "").lower()
            if trader not in [t.lower() for t in TRADERS]:
                return
            
            # Process whale trade
            await self.process_trade(trade, trader)
            
        except Exception as e:
            print(f"Error handling message: {e}")
    
    async def process_trade(self, trade, trader):
        """Copy a whale trade."""
        title = trade.get("title", "Unknown")
        size = float(trade.get("size", 0))
        side = trade.get("side", "BUY")
        outcome = trade.get("outcome", "yes")
        
        print(f"\n🎯 Whale trade from {trader[:10]}:")
        print(f"   Market: {title[:50]}...")
        print(f"   Size: ${size:.2f}")
        print(f"   Side: {side} {outcome}")
        
        # Calculate our size
        our_size = min(size * 0.05, self.max_position)
        if our_size < 0.5:
            print(f"   ⚠️ Too small (${our_size:.2f}), skipping")
            return
        
        if self.total_exposure + our_size > self.max_total:
            print(f"   ⚠️ Max exposure reached (${self.total_exposure:.2f})")
            return
        
        if self.dry_run:
            print(f"   🧪 Would copy ${our_size:.2f}")
        else:
            print(f"   📤 Copying ${our_size:.2f}...")
            # TODO: Execute actual trade
        
        self.total_exposure += our_size
    
    async def run(self):
        """Main loop."""
        print("="*60)
        print("PM COPY BOT - RTDS WebSocket")
        print("="*60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Monitoring {len(TRADERS)} whales...")
        print("")
        
        await self.connect()


if __name__ == "__main__":
    bot = PMWebSocketBot()
    asyncio.run(bot.run())
