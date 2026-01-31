#!/usr/bin/env python3
"""Aggressive copy trading monitor for FollowMeABC123."""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TRADER = os.getenv("USER_ADDRESSES", "").split(",")[0]
OUR_BANKROLL = float(os.getenv("BANKROLL", "433"))
TRADER_BANKROLL = 10000.0
MULTIPLIER = 2.0
MAX_PCT = 0.20

RATIO = OUR_BANKROLL / TRADER_BANKROLL
MAX_POSITION = OUR_BANKROLL * MAX_PCT

API_URL = "https://data-api.polymarket.com"
last_tx = None

def calculate_copy(trader_bet: float, avg_bet: float = 100.0) -> dict:
    """Calculate copy with aggressive settings."""
    pct_of_avg = trader_bet / avg_bet if avg_bet > 0 else 1.0
    
    base = trader_bet * RATIO
    our_share = base * MULTIPLIER
    
    if pct_of_avg > 1.5:
        our_share *= 1.2
    elif pct_of_avg < 0.5:
        our_share *= 0.8
    
    our_share = min(our_share, MAX_POSITION)
    our_share = max(round(our_share, 2), 1.0)
    
    return {
        "size": our_share,
        "pct_of_avg": pct_of_avg * 100,
        "pct_of_bank": our_share / OUR_BANKROLL * 100
    }

async def monitor():
    global last_tx
    
    print("=" * 70)
    print("AGGRESSIVE COPY TRADING - FollowMeABC123")
    print("=" * 70)
    print(f"Trader: {TRADER[:20]}...")
    print(f"Our Bankroll: ${OUR_BANKROLL}")
    print(f"Ratio: {RATIO*100:.2f}% | Multiplier: {MULTIPLIER}x | Max: ${MAX_POSITION:.2f}")
    print()
    print("Monitoring... (Ctrl+C to stop)")
    print("-" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                resp = await client.get(f"{API_URL}/activity", params={"user": TRADER})
                
                if resp.status_code == 200:
                    data = resp.json()
                    trades = [t for t in data if t.get("type") == "TRADE"]
                    
                    if trades:
                        latest = trades[0]
                        tx_hash = latest.get("transactionHash", "")
                        
                        if tx_hash and tx_hash != last_tx:
                            last_tx = tx_hash
                            
                            size = float(latest.get("usdcSize", 0))
                            side = latest.get("side", "")
                            price = float(latest.get("price", 0))
                            title = latest.get("title", "Unknown")[:40]
                            outcome = latest.get("outcome", "")
                            
                            copy_info = calculate_copy(size)
                            
                            now = datetime.now().strftime("%H:%M:%S")
                            
                            print()
                            print(f"🚨 [{now}] NEW TRADE SIGNAL")
                            print(f"   📊 {title}")
                            print(f"   🎯 {outcome} @ ${price}")
                            print(f"   💰 Trader: {side} ${size:.2f} ({copy_info['pct_of_avg']:.0f}% of avg)")
                            print(f"   {'='*50}")
                            print(f"   💵 OUR COPY: ${copy_info['size']:.2f} ({copy_info['pct_of_bank']:.1f}% of bankroll)")
                            print(f"   {'='*50}")
                            
                            if copy_info["size"] >= 20:
                                print(f"   🔥 Nice position! ${copy_info['size']:.2f}")
                            elif copy_info["size"] >= 10:
                                print(f"   ✅ Good size: ${copy_info['size']:.2f}")
                            else:
                                print(f"   📊 Conservative: ${copy_info['size']:.2f}")
                            
                            print("-" * 70)
                    
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\n\nStopped.")
